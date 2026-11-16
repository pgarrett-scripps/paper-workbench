import json
from pathlib import Path
import tempfile
import unittest

from peerreviewagents import verify_workspace
from peerreviewagents.workspace import digest, read_json

from paper_workspace.scaffold_import import PARSER, import_scaffold, scaffold_spans


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

    def imported(self):
        """Import the source and return the manifest, the base and its spans entries, each with its line text."""
        output = self.root / "workspace"
        manifest = import_scaffold(self.source, output)
        base = verify_workspace(output)
        entries = [{**entry, "text": base.line_text(entry["lines"][0])}
                   for entry in scaffold_spans(output, base)["paper.md"]]
        return manifest, base, entries

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

        manifest, base, entries = self.imported()

        self.assertEqual((manifest["parser"], manifest["title"]), (PARSER, "Fixture paper"))
        self.assertEqual(manifest["source"]["file"], "scaffold/paper.typ")
        self.assertEqual(base.line_text(1), "# Fixture paper")
        editable = [entry for entry in entries if entry["editable"]]
        self.assertEqual([entry["text"] for entry in editable],
                         ["A plain paragraph with ordinary punctuation (and detail).",
                          "A citation makes this paragraph complex @doe2024."])
        entry = editable[0]
        copied = output / "scaffold" / entry["file"]
        source = copied.read_bytes().decode("utf-8")
        self.assertEqual(source[entry["start"]:entry["end"]], entry["text"])
        self.assertEqual(entry["file_sha256"], digest(copied.read_bytes()))
        self.assertFalse((output / "scaffold/build").exists())
        self.assertTrue((output / "scaffold/figure.png").is_file())
        self.assertIn("doe2024", {row["id"] for row in read_json(output / "references.json")})
        verify_workspace(output)
        files = json.loads((output / "manifest.json").read_text())["files"]
        self.assertIn("scaffold/paper.typ", files)
        self.assertIn("scaffold/figure.png", files)
        self.assertIn("scaffold-spans.json", files)

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

        _, _, entries = self.imported()
        by_text = {entry["text"]: entry for entry in entries}

        for text, filename in (("Included plain prose.", "scaffold/chapters/methods.typ"),
                               ("Nested plain prose.", "scaffold/chapters/nested.typ")):
            entry = by_text[text]
            self.assertTrue(entry["editable"])
            self.assertEqual(entry["file"], filename.removeprefix("scaffold/"))
            copied = (self.root / "workspace" / filename).read_bytes().decode("utf-8")
            self.assertEqual(copied[entry["start"]:entry["end"]], text)

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

        _, _, entries = self.imported()
        self.assertEqual([entry["text"] for entry in entries if entry["editable"]], ["Plain first paragraph."])
        heading = next(entry for entry in entries if entry["kind"] == "heading")
        self.assertEqual((heading["text"], heading["editable"]), ("## Immediate heading", False))
        nested = next(entry for entry in entries if "Caption text stays inside the figure" in entry["text"])
        self.assertEqual((nested["kind"], nested["editable"]), ("source", False))

    def test_crlf_offsets_use_unmodified_utf8_text(self):
        source = (
            "// >>> BODY START\r\n"
            "= Results\r\n"
            "A CRLF paragraph keeps exact offsets.\r\n\r\n"
            "Text with _markup_ is locked.\r\n"
            "// <<< BODY END\r\n"
        )
        (self.source / "paper.typ").write_bytes(source.encode("utf-8"))

        _, _, entries = self.imported()
        entry = next(entry for entry in entries if entry["editable"])
        copied = (self.root / "workspace" / "scaffold" / entry["file"]).read_bytes().decode("utf-8")

        self.assertEqual(copied[entry["start"]:entry["end"]], entry["text"])
        self.assertIn("\r\n", copied)

    def test_a_manifest_inside_the_source_tree_is_hashed(self):
        # The engine's file_digests covers every file but the workspace's own manifest.json, so a
        # manifest.json inside the Typst tree is hashed and verify_workspace counts it like any other file.
        self.write_paper("Plain prose.")
        vendor = self.source / "vendor"
        vendor.mkdir()
        (vendor / "manifest.json").write_text('{"source": true}\n')
        output = self.root / "workspace"
        import_scaffold(self.source, output)
        self.assertIn("scaffold/vendor/manifest.json", read_json(output / "manifest.json")["files"])

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
