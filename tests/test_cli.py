from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from site_file_grabber.cli import (
    completed_download_candidates,
    extract_google_result_urls,
    extract_links,
    has_target_extension,
    host_matches,
    normalize_extensions,
    normalize_site,
    page_needs_human_verification,
    render_banner,
    render_text,
    resolve_output_dir,
    sanitize_filename,
    wayback_raw_url,
)


class CliHelpersTest(unittest.TestCase):
    def test_normalize_extensions(self) -> None:
        self.assertEqual(normalize_extensions("PDF, .Docx, jpg"), {"pdf", "docx", "jpg"})

    def test_normalize_site_adds_scheme(self) -> None:
        self.assertEqual(normalize_site("example.com"), "https://example.com/")
        self.assertEqual(normalize_site("http://example.com/path?q=1"), "http://example.com/path")

    def test_relative_output_dir_resolves_from_launch_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(resolve_output_dir("files", root), root / "files")

    def test_extension_matching_ignores_query(self) -> None:
        self.assertTrue(has_target_extension("https://example.com/a/report.PDF?download=1", {"pdf"}))
        self.assertFalse(has_target_extension("https://example.com/a/report.pdfx", {"pdf"}))

    def test_extract_links_absolutizes_attrs_and_text_urls(self) -> None:
        html = b'<a href="/file.pdf">x</a><img src="https://cdn.example.com/a.jpg"><p>https://example.com/b.docx</p>'
        links = extract_links("https://example.com/base/", html)
        self.assertIn("https://example.com/file.pdf", links)
        self.assertIn("https://cdn.example.com/a.jpg", links)
        self.assertIn("https://example.com/b.docx", links)

    def test_google_redirect_extraction(self) -> None:
        html = b'<a href="/url?q=https%3A%2F%2Fexample.com%2Ffile.pdf&sa=U">result</a>'
        self.assertEqual(
            extract_google_result_urls("https://www.google.com/search?q=x", html),
            ["https://example.com/file.pdf"],
        )

    def test_google_url_parameter_extraction(self) -> None:
        html = b'<a href="/url?sa=t&url=https%3A%2F%2Fexample.com%2Fuploads%2Fform.pdf&ved=x">result</a>'
        self.assertEqual(
            extract_google_result_urls("https://www.google.com/search?q=x", html),
            ["https://example.com/uploads/form.pdf"],
        )

    def test_google_encoded_url_extraction(self) -> None:
        html = b'AF_initDataCallback({data:"https%3A%2F%2Fexample.com%2Fuploads%2Ffile.pdf"});'
        self.assertEqual(
            extract_google_result_urls("https://www.google.com/search?q=x", html),
            ["https://example.com/uploads/file.pdf"],
        )

    def test_duckduckgo_redirect_extraction(self) -> None:
        html = b'<a href="/l/?kh=-1&uddg=https%3A%2F%2Fexample.com%2Fuploads%2Ffile.pdf">result</a>'
        self.assertEqual(
            extract_google_result_urls("https://html.duckduckgo.com/html/?q=x", html),
            ["https://example.com/uploads/file.pdf"],
        )

    def test_yahoo_redirect_extraction(self) -> None:
        html = (
            b'<a href="https://r.search.yahoo.com/_ylt=x/RV=2/RE=1/RO=10/'
            b'RU=https%3a%2f%2fexample.com%2fuploads%2ffile.pdf/RK=2/RS=x">result</a>'
        )
        self.assertEqual(
            extract_google_result_urls("https://search.yahoo.com/search?p=x", html),
            ["https://example.com/uploads/file.pdf"],
        )

    def test_host_matches_subdomains(self) -> None:
        self.assertTrue(host_matches("example.com", "https://www.example.com/file.pdf"))
        self.assertFalse(host_matches("example.com", "https://notexample.com/file.pdf"))

    def test_sanitize_filename(self) -> None:
        self.assertEqual(sanitize_filename("../../bad name.pdf"), "bad_name.pdf")

    def test_wayback_raw_url(self) -> None:
        self.assertEqual(
            wayback_raw_url("https://example.com/file.pdf"),
            "https://web.archive.org/web/0id_/https://example.com/file.pdf",
        )

    def test_render_banner_uses_filled_block_font(self) -> None:
        banner = render_banner()
        self.assertIn("Barbie Bitch Cult - Site File Grabber", banner)
        self.assertIn("█", banner)
        self.assertEqual(len(render_text("BARBIE")), 7)

    def test_security_verification_detection(self) -> None:
        class Driver:
            current_url = "https://example.com/"
            page_source = "Performing security verification. Ray ID: abc. Cloudflare."

        self.assertTrue(page_needs_human_verification(Driver()))

    def test_completed_download_candidates_ignores_partials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before = {}
            complete = root / "file.pdf"
            partial = root / "file.pdf.crdownload"
            complete.write_bytes(b"%PDF")
            partial.write_bytes(b"partial")
            self.assertEqual(completed_download_candidates(root, before), [complete])


if __name__ == "__main__":
    unittest.main()
