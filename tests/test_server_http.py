"""Local viewer server: Host validation on every method and safe page rendering."""
import http.client
import json
import os
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from peerreviewagents.engine.storage import digest, write

from paper_workspace import server as server_module
from paper_workspace.server import make_server


class ServerHttpTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        text = 'A claim with 12 samples.'
        write(self.root / 'paper.json', {'id': 'qa', 'title': 'QA', 'source_sha256': 'qa',
            'blocks': [{'id': 'b1', 'text': text, 'sha256': digest(text)}],
            'statistics': {'pdf_pages': 2}})
        write(self.root / 'manifest.json', {'files': {
            'paper.json': digest((self.root / 'paper.json').read_bytes())}})
        self.server = make_server(self.root, 0)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.temporary.cleanup()

    def request(self, path, host=None, method='GET', body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        headers = {'Host': host or f'127.0.0.1:{self.port}', **(headers or {})}
        if body is not None:
            headers['Content-Type'] = 'application/json'
            body = json.dumps(body).encode()
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def request_without_host(self, path, method='GET'):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        try:
            connection.putrequest(method, path, skip_host=True)
            connection.endheaders()
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def test_missing_host_is_rejected(self):
        for path in ('/', '/api/paper', '/pages/1.png'):
            status, body = self.request_without_host(path)
            self.assertEqual((status, json.loads(body)), (403, {'error': 'Local host required'}), path)
        self.assertEqual(self.request_without_host('/api/decisions', 'POST')[0], 403)

    def test_head_and_options_check_host_and_stay_unsupported(self):
        for method in ('HEAD', 'OPTIONS'):
            self.assertEqual(self.request('/api/paper', 'attacker.example', method)[0], 403, method)
            self.assertEqual(self.request('/api/paper', f'localhost:{self.port}', method)[0], 501, method)
        status, body = self.request('/api/paper', 'attacker.example', 'HEAD')
        self.assertEqual(body, b'')

    def test_post_requires_a_same_origin_request(self):
        for origin in ('http://attacker.example', 'null', 'http://localhost:1', f'https://localhost:{self.port}'):
            status, body = self.request('/api/decisions', method='POST', body={'review_id': 'missing'},
                                        headers={'Origin': origin})
            self.assertEqual((status, json.loads(body)), (403, {'error': 'Same-origin request required'}),
                             origin)
        for origin in (f'http://127.0.0.1:{self.port}', f'http://localhost:{self.port}'):
            status, _ = self.request('/api/decisions', method='POST', body={'review_id': 'missing'},
                                     headers={'Origin': origin})
            self.assertEqual(status, 400, origin)

    def test_stale_render_folders_are_removed_on_start(self):
        folder = self.root / 'page_images'
        (folder / '.render-old').mkdir(parents=True)
        (folder / '.render-old' / 'page.png').write_bytes(b'partial')
        (folder / '.render-live').mkdir()
        old = time.time() - server_module.STALE_RENDER_SECONDS - 60
        os.utime(folder / '.render-old', (old, old))
        make_server(self.root, 0).server_close()
        self.assertEqual(sorted(path.name for path in folder.iterdir()), ['.render-live'])

    def test_foreign_host_is_rejected_on_every_method_and_route(self):
        foreign = (f'attacker.example:{self.port}', 'attacker.example', 'localhost:1')
        paths = ('/', '/app.js', '/style.css', '/api/paper', '/api/reviews',
                 '/original.pdf', '/pages/1.png', '/scaffold/main.typ')
        with patch.object(server_module.subprocess, 'run', side_effect=AssertionError('rendered')):
            for host in foreign:
                for path in paths:
                    status, body = self.request(path, host)
                    self.assertEqual((status, json.loads(body)), (403, {'error': 'Local host required'}),
                                     (host, path))
                for method in ('POST', 'PUT', 'DELETE'):
                    status, _ = self.request('/api/decisions', host, method, {'review_id': 'qa'})
                    self.assertEqual(status, 403, (host, method))
        self.assertFalse((self.root / 'page_images').exists())

    def test_local_hosts_are_served(self):
        for host in (f'127.0.0.1:{self.port}', f'localhost:{self.port}'):
            status, body = self.request('/api/paper', host)
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)['id'], 'qa')
            status, body = self.request('/', host)
            self.assertEqual(status, 200)
            self.assertIn(b'<', body)
            status, _ = self.request('/api/decisions', host, 'POST', {'review_id': 'missing'})
            self.assertEqual(status, 400)
            status, _ = self.request('/api/paper', host, 'PUT')
            self.assertEqual(status, 501)

    def test_viewer_shell_skips_verification_but_data_routes_keep_it(self):
        with patch.object(server_module, 'snapshot', side_effect=AssertionError('verified')):
            for path in ('/', '/index.html', '/app.js', '/style.css'):
                self.assertEqual(self.request(path)[0], 200, path)
        (self.root / 'paper.json').write_text('{"id": "changed"}')
        self.assertEqual(self.request('/')[0], 200)
        status, body = self.request('/api/paper')
        self.assertEqual(status, 400)
        self.assertIn('Manuscript source changed', json.loads(body)['error'])

    def test_page_render_failure_returns_a_short_error_and_leaves_no_image(self):
        def fail(command, **kwargs):
            raise subprocess.CalledProcessError(1, command)

        for failure in (fail, subprocess.TimeoutExpired(['pdftoppm', str(self.root)], 30)):
            with patch.object(server_module.subprocess, 'run', side_effect=failure):
                status, body = self.request('/pages/1.png')
            self.assertEqual((status, json.loads(body)),
                             (400, {'error': 'Could not render page 1 of the original PDF'}))
            self.assertEqual(list((self.root / 'page_images').iterdir()), [])

    def test_concurrent_page_request_never_reads_a_partial_image(self):
        image = b'\x89PNG' + b'x' * 4096
        half_written, release = threading.Event(), threading.Event()
        calls, results = [], {}

        def render(command, **kwargs):
            calls.append(command)
            with Path(command[-1] + '.png').open('wb') as stream:
                stream.write(image[:100])
                stream.flush()
                half_written.set()
                release.wait(10)
                stream.write(image[100:])
            return subprocess.CompletedProcess(command, 0)

        def fetch(key):
            results[key] = self.request('/pages/1.png')

        with patch.object(server_module.subprocess, 'run', side_effect=render):
            first = threading.Thread(target=fetch, args=('first',))
            first.start()
            self.assertTrue(half_written.wait(10))
            second = threading.Thread(target=fetch, args=('second',))
            second.start()
            second.join(0.5)
            release.set()
            first.join(10)
            second.join(10)
        self.assertEqual(results['first'], (200, image))
        self.assertEqual(results['second'], (200, image))
        self.assertEqual(len(calls), 1)
        self.assertEqual(sorted(path.name for path in (self.root / 'page_images').iterdir()), ['001.png'])


if __name__ == '__main__':
    unittest.main()
