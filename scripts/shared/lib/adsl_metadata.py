from __future__ import annotations
"""Shared ADSL metadata embedding, parsing, and filename helper library."""

import re
from pathlib import Path


def parse_adsl_metadata(dsl_text_or_filepath: str | Path) -> dict[str, str | None]:
    """Parse structured header metadata from ADSL text or file.

    Supports fields:
      # @presentation_id: <pres_id>
      # @slide_id: <slide_id>
      # @purpose: <purpose_slug>
      # @category: <category_name>
      # @description: <brief_structural_description>
      # @keywords: <comma_separated_keywords>

    Args:
        dsl_text_or_filepath: ADSL text string or Path to an .adsl file.

    Returns:
        Dict containing extracted metadata fields (or None if missing/empty).
    """
    text = ""
    if isinstance(dsl_text_or_filepath, Path):
        text = dsl_text_or_filepath.read_text(encoding="utf-8")
    elif isinstance(dsl_text_or_filepath, str):
        if "\n" not in dsl_text_or_filepath and len(dsl_text_or_filepath) < 1024:
            p = Path(dsl_text_or_filepath)
            if p.is_file():
                text = p.read_text(encoding="utf-8")
            else:
                text = dsl_text_or_filepath
        else:
            text = dsl_text_or_filepath

    m_pres = re.search(r"^\s*#\s*@presentation_id:\s*(.*)$", text, re.MULTILINE)
    m_slide = re.search(r"^\s*#\s*@slide_id:\s*(.*)$", text, re.MULTILINE)
    m_purpose = re.search(r"^\s*#\s*@purpose:\s*(.*)$", text, re.MULTILINE)
    m_category = re.search(r"^\s*#\s*@category:\s*(.*)$", text, re.MULTILINE)
    m_desc = re.search(r"^\s*#\s*@description:\s*(.*)$", text, re.MULTILINE)
    m_kw = re.search(r"^\s*#\s*@keywords:\s*(.*)$", text, re.MULTILINE)

    def _clean_val(match: re.Match | None) -> str | None:
        if not match:
            return None
        val = match.group(1).strip()
        return val if val else None

    return {
        "presentation_id": _clean_val(m_pres),
        "slide_id": _clean_val(m_slide),
        "purpose": _clean_val(m_purpose),
        "category": _clean_val(m_category),
        "description": _clean_val(m_desc),
        "keywords": _clean_val(m_kw),
    }


def embed_adsl_metadata(
    dsl: str,
    presentation_id: str | int | None = None,
    slide_id: str | int | None = None,
    purpose: str | None = None,
    category: str | None = None,
    description: str | None = None,
    keywords: str | list[str] | None = None,
) -> str:
    """Embed or update structured metadata header comments at the top of ADSL content.

    Args:
        dsl: The ADSL text content.
        presentation_id: Presentation ID to embed.
        slide_id: Slide ID to embed.
        purpose: Purpose slug to embed.
        category: Category name to embed.
        description: Brief structural description to embed.
        keywords: Keywords string or list of keyword strings to embed.

    Returns:
        ADSL content with updated metadata header comments formatted cleanly before frontmatter.
    """
    pres_str = (
        str(presentation_id).strip()
        if presentation_id is not None and str(presentation_id).strip() != ""
        else None
    )
    slide_str = (
        str(slide_id).strip()
        if slide_id is not None and str(slide_id).strip() != ""
        else None
    )
    purpose_str = (
        str(purpose).strip()
        if purpose is not None and str(purpose).strip() != ""
        else None
    )
    category_str = (
        str(category).strip()
        if category is not None and str(category).strip() != ""
        else None
    )
    desc_str = (
        str(description).strip()
        if description is not None and str(description).strip() != ""
        else None
    )
    if isinstance(keywords, (list, tuple)):
        kw_str = ", ".join(str(k).strip() for k in keywords if str(k).strip())
        kw_str = kw_str if kw_str else None
    elif keywords is not None and str(keywords).strip() != "":
        kw_str = str(keywords).strip()
    else:
        kw_str = None

    # Parse existing metadata if current arguments are None
    existing = parse_adsl_metadata(dsl)
    if pres_str is None:
        pres_str = existing.get("presentation_id")
    if slide_str is None:
        slide_str = existing.get("slide_id")
    if purpose_str is None:
        purpose_str = existing.get("purpose")
    if category_str is None:
        category_str = existing.get("category")
    if desc_str is None:
        desc_str = existing.get("description")
    if kw_str is None:
        kw_str = existing.get("keywords")

    # Clean existing @header comment lines from DSL
    cleaned_dsl = re.sub(
        r"^\s*#\s*@(presentation_id|slide_id|purpose|category|description|keywords):.*(?:\r?\n)?",
        "",
        dsl,
        flags=re.MULTILINE,
    )

    # Strip leading blank lines left at start
    cleaned_dsl = re.sub(r"^(?:\r?\n)+", "", cleaned_dsl)

    header_lines = []
    if pres_str is not None:
        header_lines.append(f"# @presentation_id: {pres_str}")
    if slide_str is not None:
        header_lines.append(f"# @slide_id: {slide_str}")
    if purpose_str is not None:
        header_lines.append(f"# @purpose: {purpose_str}")
    if category_str is not None:
        header_lines.append(f"# @category: {category_str}")
    if desc_str is not None:
        header_lines.append(f"# @description: {desc_str}")
    if kw_str is not None:
        header_lines.append(f"# @keywords: {kw_str}")

    if not header_lines:
        return cleaned_dsl

    header_text = "\n".join(header_lines) + "\n"
    return header_text + cleaned_dsl


REQUIRED_METADATA_KEYS = ("presentation_id", "slide_id", "purpose")


def lint_adsl_metadata(dsl_text: str, filename: str | Path | None = None) -> list[str]:
    """Lint ADSL header metadata comments and verify filename consistency.

    Checks:
      a) Presence of required header comments (# @presentation_id, # @slide_id, # @purpose).
      b) Non-empty metadata values.
      c) Consistency between filename values and internal # @ comments.
      d) Valid # @key: value comment formatting.

    Args:
        dsl_text: Content of the ADSL file.
        filename: Optional filename or Path for cross-checking filename vs header comments.

    Returns:
        List of error strings found during linting (empty list if 0 errors).
    """
    errors: list[str] = []

    # Check d) Valid formatting of header comment lines starting with # @
    for i, line in enumerate(dsl_text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("# @"):
            m = re.match(r"^#\s*@([a-zA-Z0-9_]+):\s*(.*)$", stripped)
            if not m:
                errors.append(
                    f"Line {i}: Invalid header comment format: '{stripped}' (expected '# @key: value')"
                )
            else:
                key, val = m.group(1), m.group(2).strip()
                if not val:
                    errors.append(f"Line {i}: Empty metadata value for '# @{key}'")

    parsed_meta = parse_adsl_metadata(dsl_text)

    # Check a) Presence of required header comments
    for req_key in REQUIRED_METADATA_KEYS:
        val = parsed_meta.get(req_key)
        if val is None or not str(val).strip():
            errors.append(f"Missing required header comment: '# @{req_key}'")

    # Check c) Consistency between filename values and internal # @ comments
    if filename:
        fn_parsed = parse_adsl_filename(filename)
        for key in ("presentation_id", "slide_id", "purpose"):
            fn_val = fn_parsed.get(key)
            meta_val = parsed_meta.get(key)
            if fn_val and meta_val and fn_val != meta_val:
                errors.append(
                    f"Mismatch between filename {key} ('{fn_val}') and header # @{key} ('{meta_val}')"
                )

    return errors


def lint_adsl_file(file_path: str | Path) -> dict:
    """Lint a single ADSL file on disk.

    Returns:
        Dict with keys: file, filename, valid, errors.
    """
    p = Path(file_path)
    if not p.is_file():
        return {
            "file": str(p),
            "filename": p.name,
            "valid": False,
            "errors": [f"File not found: {p}"],
        }

    content = p.read_text(encoding="utf-8")
    errors = lint_adsl_metadata(content, filename=p.name)
    return {
        "file": str(p),
        "filename": p.name,
        "valid": len(errors) == 0,
        "errors": errors,
    }


def format_adsl_filename(
    title_or_purpose: str,
    presentation_id: str | int | None = None,
    slide_id: str | int | None = None,
) -> str:
    """Format an ADSL template filename as {purpose}_{presentation_id}_{slide_id}.adsl.

    Args:
        title_or_purpose: Descriptive title or purpose string.
        presentation_id: Presentation ID.
        slide_id: Slide ID.

    Returns:
        Formatted filename string ending in .adsl.
    """
    clean_title = title_or_purpose.strip()
    if clean_title.lower().endswith(".adsl"):
        clean_title = clean_title[:-5]
    elif clean_title.lower().endswith(".dsl"):
        clean_title = clean_title[:-4]

    clean_purpose = re.sub(r"[^a-zA-Z0-9]+", "_", clean_title.lower()).strip("_")
    if not clean_purpose:
        clean_purpose = "slide"

    pres_str = (
        str(presentation_id).strip()
        if presentation_id is not None and str(presentation_id).strip() != ""
        else None
    )
    slide_str = (
        str(slide_id).strip()
        if slide_id is not None and str(slide_id).strip() != ""
        else None
    )

    parts = [clean_purpose]
    if pres_str:
        parts.append(pres_str)
    if slide_str:
        parts.append(slide_str)

    return f"{'_'.join(parts)}.adsl"


def parse_adsl_filename(filename_or_path: str | Path) -> dict[str, str | None]:
    """Extract purpose, presentation_id, and slide_id from an ADSL filename.

    Supports patterns:
      {purpose}_{presentation_id}_{slide_id}.adsl
      {purpose}_{slide_id}.adsl
      {slide_id}.adsl
      {purpose}.adsl

    Args:
        filename_or_path: Filename string or Path.

    Returns:
        Dict containing 'purpose', 'presentation_id', and 'slide_id'.
    """
    name = Path(filename_or_path).name
    stem = name
    if stem.lower().endswith(".adsl"):
        stem = stem[:-5]
    elif stem.lower().endswith(".dsl"):
        stem = stem[:-4]

    m_three = re.match(r"^(.+)_(\d+)_(\d+)$", stem)
    if m_three:
        return {
            "purpose": m_three.group(1),
            "presentation_id": m_three.group(2),
            "slide_id": m_three.group(3),
        }

    m_two = re.match(r"^(.+)_(\d+)$", stem)
    if m_two:
        return {
            "purpose": m_two.group(1),
            "presentation_id": None,
            "slide_id": m_two.group(2),
        }

    m_one = re.match(r"^(\d+)$", stem)
    if m_one:
        return {
            "purpose": None,
            "presentation_id": None,
            "slide_id": m_one.group(1),
        }

    return {
        "purpose": stem,
        "presentation_id": None,
        "slide_id": None,
    }

