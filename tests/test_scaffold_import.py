import json
from pathlib import Path
import tempfile
import unittest

from peerreviewagents import verify_workspace
from peerreviewagents.workspace import digest

from paper_workspace.scaffold_import import import_scaffold


class ScaffoldImportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "config.typ").write_text('#let paper-title = "Fixture paper"\n')

    def write_paper(self, body):
        (self.source / "paper.typ").write_text(
            "#import \"config.typ\": *\n"
            "// >>> BODY START\n" + body + "\n// <<< BODY END\n"
        )

    def test_import_copies_baseline_and_records_exact_editable_spans(self):
        self.write_paper(
            "= Introduction\n\n"
            "A plain paragraph with ordinary punctuation (and detail).\n\n"
            "A citation makes this paragraph complex @doe2024.\n\n"
            "#figure(rect(width: 1cm), caption: [Locked caption.]) <fig:one>"
        )
        (self.source / "references.bib").write_text(
            "@article{doe2024, title={A reference}, year={2024}}\n"
        )
        (self.source / "figure.png").write_bytes(b"png")
        (self.source / "build").mkdir()
        (self.source / "build" / "paper.pdf").write_bytes(b"generated")
        output = self.root / "workspace"

        paper = import_scaffold(self.source, output)

        self.assertEqual(paper["source_format"], "scaffold-typst")
        self.assertEqual(paper["title"], "Fixture paper")
        editable = [block for block in paper["blocks"] if block["editable"]]
        self.assertEqual([block["text"] for block in editable],
                         ["A plain paragraph with ordinary punctuation (and detail).",
                          "A citation makes this paragraph complex @doe2024."])
        block = editable[0]
        span = block["source_span"]
        copied = output / "scaffold" / span["file"]
        source = copied.read_bytes().decode("utf-8")
        self.assertEqual(source[span["start"]:span["end"]], block["text"])
        self.assertEqual(span["file_sha256"], digest(copied.read_bytes()))
        self.assertFalse((output / "scaffold/build").exists())
        self.assertTrue((output / "scaffold/figure.png").is_file())
        self.assertIn("doe2024", {row["id"] for row in paper["references"]})
        self.assertEqual(verify_workspace(output), paper)
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertIn("scaffold/paper.typ", manifest["files"])
        self.assertIn("scaffold/figure.png", manifest["files"])

    def test_literal_body_includes_are_recursive_and_keep_file_offsets(self):
        chapters = self.source / "chapters"
        chapters.mkdir()
        (chapters / "nested.typ").write_text("Nested plain prose.\n")
        chapter_source = (
            "// >>> BODY START\n"
            "Included plain prose.\n\n"
            "#include \"nested.typ\"\n"
            "// <<< BODY END\n"
        )
        (chapters / "methods.typ").write_text(chapter_source)
        self.write_paper("= Methods\n\n#include \"chapters/methods.typ\"")

        output = self.root / "workspace"
        paper = import_scaffold(self.source, output)
        by_text = {block["text"]: block for block in paper["blocks"]}

        for text, filename in (("Included plain prose.", "scaffold/chapters/methods.typ"),
                               ("Nested plain prose.", "scaffold/chapters/nested.typ")):
            block = by_text[text]
            self.assertTrue(block["editable"])
            relative = filename.removeprefix("scaffold/")
            self.assertEqual(block["source_span"]["file"], relative)
            copied = (output / filename).read_bytes().decode("utf-8")
            span = block["source_span"]
            self.assertEqual(copied[span["start"]:span["end"]], text)

    def test_complex_typst_and_nested_content_are_locked(self):
        self.write_paper(
            "= Immediate heading\n"
            "Plain first paragraph.\n\n"
            "Text with *emphasis* remains locked.\n\n"
            "$ x + y $\n\n"
            "$ x +\n\nplain looking math\n\n+ y $\n\n"
            "```python\nprint('kept')\n```\n\n"
            "```text\nfirst raw line\n\nplain looking raw line\n```\n\n"
            "#figure(\n  rect(width: 1cm),\n\n  caption: [Caption text stays inside the figure.],\n) <fig:nested>"
        )

        paper = import_scaffold(self.source, self.root / "workspace")
        editable = [block["text"] for block in paper["blocks"] if block["editable"]]
        self.assertEqual(editable, ["Plain first paragraph."])
        heading = next(block for block in paper["blocks"] if block["kind"] == "heading")
        self.assertIsNone(heading["source_span"])
        nested = next(block for block in paper["blocks"]
                      if "Caption text stays inside the figure" in block["text"])
        self.assertTrue(nested["locked"])
        self.assertEqual(nested["kind"], "source")
        self.assertIsNone(nested["source_span"])

    def test_crlf_offsets_use_unmodified_utf8_text_and_nested_manifests_are_hashed(self):
        source = (
            "// >>> BODY START\r\n"
            "= Results\r\n"
            "A CRLF paragraph keeps exact offsets.\r\n\r\n"
            "Text with _markup_ is locked.\r\n"
            "// <<< BODY END\r\n"
        )
        (self.source / "paper.typ").write_bytes(source.encode("utf-8"))
        vendor = self.source / "vendor"
        vendor.mkdir()
        (vendor / "manifest.json").write_text('{"source": true}\n')
        output = self.root / "workspace"

        paper = import_scaffold(self.source, output)
        block = next(block for block in paper["blocks"] if block["editable"])
        span = block["source_span"]
        copied = (output / "scaffold" / span["file"]).read_bytes().decode("utf-8")

        self.assertEqual(copied[span["start"]:span["end"]], block["text"])
        self.assertIn("\r\n", copied)
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertIn("scaffold/vendor/manifest.json", manifest["files"])

    def test_rejects_ambiguous_markers_unsafe_includes_symlinks_and_nonempty_output(self):
        cases = (
            ("// >>> BODY START\nOne.\n// >>> BODY START\nTwo.\n// <<< BODY END\n", "BODY START"),
            ("// >>> BODY START\n#include \"../outside.typ\"\n// <<< BODY END\n", "Unsafe Scaffold include"),
        )
        for index, (source, message) in enumerate(cases):
            with self.subTest(message=message):
                (self.source / "paper.typ").write_text(source)
                with self.assertRaisesRegex(ValueError, message):
                    import_scaffold(self.source, self.root / f"workspace-{index}")

        self.write_paper("Plain prose.")
        (self.source / "linked.typ").symlink_to(self.source / "paper.typ")
        with self.assertRaisesRegex(ValueError, "symlink"):
            import_scaffold(self.source, self.root / "workspace-link")
        (self.source / "linked.typ").unlink()

        output = self.root / "nonempty"
        output.mkdir()
        (output / "keep.txt").write_text("keep")
        with self.assertRaisesRegex(ValueError, "must not exist or must be empty"):
            import_scaffold(self.source, output)
        self.assertEqual((output / "keep.txt").read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
