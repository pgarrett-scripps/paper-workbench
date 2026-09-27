"""Durable stage state with process identity and interruption detection."""
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from .storage import read, write


def process_namespace():
    try:
        return os.readlink('/proc/self/ns/pid')
    except OSError:
        return None


def process_identity(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        if fields[0] == 'Z':
            return None
        return Path('/proc/sys/kernel/random/boot_id').read_text().strip()+':'+fields[19]
    except (OSError, IndexError):
        return None


def inspect_state(path):
    """Derive stale status without rewriting the historical stage record."""
    value = read(path)
    if value.get('status') == 'running':
        namespace = process_namespace()
        if not namespace or value.get('process_namespace') != namespace:
            return {**value, 'status': 'unverified', 'recorded_status': 'running',
                    'reason': 'Inspect from the owning process namespace before declaring interruption or retrying.'}
        identity = process_identity(value.get('pid'))
        if not identity or identity != value.get('process_identity'):
            return {**value, 'status': 'interrupted', 'reason': 'Owning process is absent or changed.',
                    'recorded_status': 'running', 'usage_requires_reconciliation': True}
        if time.time() > value.get('deadline_at', float('inf')):
            return {**value, 'status': 'overdue', 'recorded_status': 'running',
                    'reason': 'Stage exceeded its expected completion deadline. Do not retry while its process is alive.'}
    return value


@contextmanager
def tracked_stage(path, label, timeout=1200):
    path = Path(path)
    pid = os.getpid()
    now = time.time()
    value = {'status': 'running', 'stage': label, 'pid': pid,
             'process_identity': process_identity(pid), 'process_namespace': process_namespace(), 'started_at': now,
             'heartbeat_at': now, 'deadline_at': now+timeout}
    write(path, value)
    stopped = threading.Event()
    def heartbeat():
        while not stopped.wait(15):
            value['heartbeat_at'] = time.time()
            write(path, value)
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        yield
    except BaseException as error:
        stopped.set()
        thread.join()
        write(path, {**value, 'status': 'interrupted' if isinstance(error, (KeyboardInterrupt, SystemExit)) else 'failed',
                     'finished_at': time.time(), 'error': str(error), 'usage_requires_reconciliation': True})
        raise
    else:
        stopped.set()
        thread.join()
        write(path, {**value, 'status': 'complete', 'finished_at': time.time()})
