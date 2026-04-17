"""
sheet_utils.py  Shared Google Sheets safe-write utilities

Provides a scan  prepare  re-scan  merge  write pattern so that
manually-added rows are NEVER erased by automated script runs.

Usage:
    from scripts.sheet_utils import safe_write_worksheet

    safe_write_worksheet(
        worksheet=ws,
        managed_headers=["Col A", "Col B"],
        managed_data=[[...], [...]],
        key_column=1,            # 0-indexed column used as the unique row key
        sheet_label="Dashboard", # used for log output only
    )
"""

import time


# 
#  Internal helpers
# 

def _scan(worksheet) -> list[list[str]]:
    """Read all current rows from a worksheet."""
    rows = worksheet.get_all_values()
    return rows if rows else []


def _extract_custom_rows(
    existing_rows: list[list[str]],
    known_keys: set[str],
    key_column: int,
    section_marker: str = "",
) -> list[list[str]]:
    """
    Return rows from existing_rows whose key value (at key_column) is NOT in
    known_keys.  Skips: the header row (index 0), fully blank rows, and any
    section-heading rows (identified by section_marker in column 0).
    """
    custom = []
    for row in existing_rows[1:]:          # skip header
        # Normalise row length
        while len(row) <= key_column:
            row.append("")

        key = row[key_column].strip()
        category = row[0].strip()

        # Skip blank rows
        if not any(cell.strip() for cell in row):
            continue
        # Skip section-heading rows
        if category.startswith(section_marker):
            continue
        # Skip rows we already manage
        if key in known_keys:
            continue

        custom.append(row)

    return custom


def _dedup(rows: list[list[str]], key_column: int) -> list[list[str]]:
    """Deduplicate rows by key_column, preserving order."""
    seen = set()
    result = []
    for row in rows:
        key = row[key_column].strip() if len(row) > key_column else ""
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result


# 
#  Public API
# 

def safe_write_worksheet(
    worksheet,
    managed_headers: list[str],
    managed_data: list[list],
    key_column: int = 1,
    sheet_label: str = "Sheet",
    section_marker: str = "",
    freeze_header: bool = True,
    header_format: dict | None = None,
    section_format: dict | None = None,
) -> int:
    """
    Safe-write a worksheet using a scan  prepare  re-scan  merge  write
    pattern.  Any rows the user has manually added are preserved at the bottom
    under a ' USER-ADDED ROWS ' section heading.

    Returns the total number of rows written (excluding the header).
    """
    # Build the set of keys we manage (used to detect custom/user rows)
    known_keys = {
        str(row[key_column]).strip()
        for row in managed_data
        if len(row) > key_column
        and str(row[key_column]).strip()
        and not str(row[0]).startswith(section_marker)
    }

    #  SCAN 1 
    print(f"  [{sheet_label}] SCAN 1: Reading existing content...")
    scan_1 = _scan(worksheet)
    print(f"  [{sheet_label}]   -> {len(scan_1)} rows found.")
    custom_1 = _extract_custom_rows(scan_1, known_keys, key_column, section_marker)
    if custom_1:
        print(f"  [{sheet_label}]   -> {len(custom_1)} user-added row(s) detected.")

    #  PREPARE 
    print(f"  [{sheet_label}] Preparing output...")

    # Brief pause so any concurrent edits have a chance to land
    time.sleep(0.5)

    #  SCAN 2 
    print(f"  [{sheet_label}] SCAN 2: Re-reading to catch late edits...")
    scan_2 = _scan(worksheet)
    print(f"  [{sheet_label}]   -> {len(scan_2)} rows found.")
    custom_2 = _extract_custom_rows(scan_2, known_keys, key_column, section_marker)

    # Detect anything added between scan 1 and scan 2
    keys_from_scan_1 = {r[key_column].strip() for r in custom_1 if len(r) > key_column}
    newly_added = [r for r in custom_2 if r[key_column].strip() not in keys_from_scan_1]
    if newly_added:
        print(f"  [{sheet_label}]   -> {len(newly_added)} new row(s) appeared between scans  including them.")

    # Merge and deduplicate custom rows from both scans
    all_custom = _dedup(custom_1 + newly_added, key_column)

    # Build the final output
    all_rows = [managed_headers] + managed_data
    if all_custom:
        all_rows.append([section_marker + " USER-ADDED ROWS " + section_marker] + [""] * (len(managed_headers) - 1))
        all_rows.extend(all_custom)
        print(f"  [{sheet_label}]   -> Appending {len(all_custom)} preserved custom row(s).")

    #  WRITE 
    print(f"  [{sheet_label}] Writing {len(all_rows)} rows...")
    worksheet.clear()
    worksheet.update(values=all_rows, range_name="A1")

    #  FORMAT 
    col_letter = chr(ord("A") + len(managed_headers) - 1)  # e.g. 4 cols -> "D"

    # Header row formatting
    _hfmt = header_format or {
        "textFormat": {"bold": True, "fontSize": 11},
        "backgroundColor": {"red": 0.13, "green": 0.13, "blue": 0.13},
    }
    try:
        worksheet.format(f"A1:{col_letter}1", _hfmt)
    except Exception:
        pass

    # Section-heading row formatting
    _sfmt = section_format or {
        "textFormat": {"bold": True, "italic": True},
        "backgroundColor": {"red": 0.85, "green": 0.92, "blue": 0.99},
    }
    try:
        for i, row in enumerate(all_rows[1:], start=2):
            if str(row[0]).startswith(section_marker):
                worksheet.format(f"A{i}:{col_letter}{i}", _sfmt)
    except Exception:
        pass

    # Freeze header row
    if freeze_header:
        try:
            worksheet.freeze(rows=1)
        except Exception:
            pass

    data_rows_written = len(all_rows) - 1
    print(f"  [{sheet_label}] Done. {data_rows_written} data row(s) written.")
    return data_rows_written
