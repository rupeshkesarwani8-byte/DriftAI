import io

import pytest

from app.services.docparse import DocumentError, clean_markdown, read_document
from app.services.drift import detect_drift


def test_txt_is_returned_as_text():
    assert read_document("req.txt", b"Login time is 10 minutes.\n") == "Login time is 10 minutes."


def test_bom_and_windows_line_endings():
    data = b"\xef\xbb\xbfA user is locked after 5 attempts.\r\nA password needs 8 characters.\r\n"
    text = read_document("req.txt", data)
    assert text.startswith("A user is locked")
    assert len(text.splitlines()) == 2


def test_markdown_drops_headings_rules_and_bold():
    md = b"# Requirements (Version 1)\n\n---\n1. A user is **locked** after 5 attempts.\n2. Use `8` characters.\n"
    text = read_document("req.md", md)
    assert "Requirements" not in text and "---" not in text
    assert "**" not in text and "`" not in text
    assert "locked after 5 attempts" in text


def test_clean_markdown_keeps_requirement_lines():
    assert clean_markdown("## Title\nKeep this line.") == "Keep this line."


def test_empty_file_is_rejected():
    with pytest.raises(DocumentError):
        read_document("req.txt", b"   \n")


def test_heading_only_markdown_is_rejected():
    with pytest.raises(DocumentError):
        read_document("req.md", b"# Only a title\n")


def test_unsupported_type_is_rejected():
    with pytest.raises(DocumentError):
        read_document("req.pdf", b"%PDF-1.4")


def test_too_big_is_rejected():
    with pytest.raises(DocumentError):
        read_document("req.txt", b"a" * 1_000_001)


def test_heading_difference_is_not_a_fake_change():
    # Without clean_markdown the two headings ("Version 1" / "Version 2") look like a changed number.
    old = read_document("v1.md", b"# Reqs (Version 1)\n1. A course can be refunded within 7 days.\n")
    new = read_document("v2.md", b"# Reqs (Version 2)\n1. A course can be refunded within 14 days.\n")
    changes = detect_drift(old, new)
    assert len(changes) == 1
    assert changes[0]["old_value"] == "7 days" and changes[0]["new_value"] == "14 days"


def test_docx_paragraphs_and_tables_are_read_and_headings_skipped():
    docx = pytest.importorskip("docx")
    doc = docx.Document()
    doc.add_heading("Requirements", level=1)
    doc.add_paragraph("A user is locked after 5 failed attempts.")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Refund"
    table.rows[0].cells[1].text = "within 7 days"
    buffer = io.BytesIO()
    doc.save(buffer)
    text = read_document("req.docx", buffer.getvalue())
    assert "Requirements" not in text
    assert "locked after 5 failed attempts" in text
    assert "Refund within 7 days" in text


def test_broken_docx_gives_a_clear_error():
    pytest.importorskip("docx")
    with pytest.raises(DocumentError):
        read_document("req.docx", b"this is not a zip file")
        