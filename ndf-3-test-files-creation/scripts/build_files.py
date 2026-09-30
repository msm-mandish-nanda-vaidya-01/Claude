"""
build_files.py — mechanical file-writing helper for the NDF 3-test-files skill.

This does NOT decide what data to put in the files (that's Claude's job, guided by
SKILL.md + references/*.md). It only handles the repetitive, error-prone mechanics:
  - writing the Input CSV with a real UTF-8 BOM and verifying it
  - writing the two xlsx files with the exact required sheets/headers
  - assembling the 3 file names from the naming convention
  - running the structural/consistency self-checks from validation_rules.md
    (see validate_files.py) before anything is called "done"

Claude should build 3 Python lists-of-dicts (input_rows, spec_grouping rows split
into specNameCommon/exception, type_grouping rows split into TypeMatch/BasicSpecDefenition)
per the scenario/edge-case plan, then call `build(...)` below rather than
hand-writing csv.writer / openpyxl code inline every time.

For the Input CSV specifically, `input_rows`/`input_header` may instead be authored as a
compact pipe-delimited header+rows text block and turned into the same list[dict]/header
shape via `parse_pipe_table()` below (see its docstring) — this saves tokens versus writing
out a Python dict literal per row. The other 4 row lists (specNameCommon, exception,
TypeMatch, BasicSpecDefenition) stay plain Python list-of-dict literals; they're capped
small enough that a second format isn't worth it there.

Usage:
    from build_files import build

    result = build(
        category_name_common="JIR A1 761",
        subsidary_cd="MJP",
        yymmdd="260722",
        scenario_tag="and_or",              # or None
        input_rows=[...],                   # list[dict], keys = CSV header names
        input_header=[...],                 # ordered list of column names
        spec_name_common_rows=[...],        # list[dict] for specNameCommon sheet
        exception_rows=[],                  # must stay [] per convention (§14)
        type_match_rows=[...],              # list[dict] for TypeMatch sheet
        basic_spec_def_rows=[...],          # list[dict] for BasicSpecDefenition (1-2 rows)
        output_dir="/mnt/user-data/outputs",
    )
    print(result["paths"])

DDB mode only (on explicit request, after build()): write the Discontinued CSV from
the same input_rows via build_discontinued(...) — see its docstring and
test_run_conventions.md §16.
"""
import csv
import os
import re


def parse_pipe_table(text, expected_header=None):
    """Parse a pipe-delimited header+rows text block into the list[dict] shape
    build()'s input_rows expects, plus the header list for input_header.

    Format: one header line (column names joined by '|'), then one line per row
    with values in the same column order, also joined by '|'. Empty cells are
    just two consecutive '|'s. Every row must have exactly as many '|'-separated
    cells as the header (pad trailing empty cells for rows with fewer spec sets
    than the widest row). Never put a literal '|' inside a cell's content.

    part_number_rules is the one documented column that's legitimately
    multi-line (one `IF [...] Rule ...;` statement per line, per
    test_run_conventions.md §8). Since a raw newline can't be told apart from a
    row boundary, encode an embedded newline inside a cell as the literal
    two-character escape '\\n' when authoring the text; this function converts
    it back to a real newline after splitting rows/columns.

    Raises ValueError (naming the line number) on a header mismatch or a row
    whose cell count doesn't match the header, so a miscounted row fails loud
    instead of silently shifting columns.
    """
    lines = [line for line in text.strip("\n").split("\n") if line != ""]
    if not lines:
        raise ValueError("empty pipe table text")
    header = lines[0].split("|")
    if expected_header is not None and header != expected_header:
        raise ValueError(f"header mismatch: got {header}, expected {expected_header}")
    rows = []
    for lineno, line in enumerate(lines[1:], start=2):
        cells = line.split("|")
        if len(cells) != len(header):
            raise ValueError(
                f"line {lineno}: expected {len(header)} columns, got {len(cells)}: {line!r}"
            )
        cells = [cell.strip().replace("\\n", "\n") for cell in cells]
        rows.append(dict(zip(header, cells)))
    return rows


def _category_to_filename_segment(category_name_common: str) -> str:
    """'JIR A1 761' -> 'JIR_A1_761' per test_run_conventions.md §6."""
    return "_".join(category_name_common.split())


def _build_filenames(category_name_common, subsidary_cd, yymmdd, scenario_tag):
    cat = _category_to_filename_segment(category_name_common)
    tag = f"_{scenario_tag}" if scenario_tag else ""
    input_name = f"Input_{cat}_{subsidary_cd}_TestFile_{yymmdd}{tag}.csv"
    spec_name = f"SpecGrouping_{cat}_{yymmdd}_TestFile{tag}.xlsx"
    type_name = f"TypeGrouping_{cat}_{yymmdd}_TestFile{tag}.xlsx"
    return input_name, spec_name, type_name


def _write_csv_with_bom(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in header})
    # verify BOM
    with open(path, "rb") as f:
        head = f.read(3)
    if head != b"\xef\xbb\xbf":
        raise RuntimeError(f"BOM missing on {path}: got {head!r}")


def _write_xlsx(path, sheets: dict):
    """sheets: {sheet_name: (header_list, rows_list_of_dict)}"""
    from openpyxl import Workbook

    wb = Workbook()
    wb.remove(wb.active)
    for sheet_name, (header, rows) in sheets.items():
        ws = wb.create_sheet(title=sheet_name)
        ws.append(header)
        for row in rows:
            ws.append([row.get(col, "") for col in header])
    wb.save(path)


SPEC_NAME_COMMON_HEADER = [
    "#", "subsidary_cd", "category_name_common", "spec_name_common",
    "stringReplacement", "calculationFormula", "unitConversionFormula",
    "exceptionBt_no", "priority_order",
]
EXCEPTION_HEADER = [
    "#", "subsidary_cd", "part_number_type", "brand_name_common", "category_name_common", "spec_name_common",
    "stringReplacement", "calculationFormula", "unitConversionFormula",
]
TYPE_MATCH_HEADER = ["#", "subsidary_cd", "category_name_common", "brand_name_common", "part_number_type"]
BASIC_SPEC_DEF_HEADER = ["#", "subsidary_cd", "category_name_common", "spec_name_common"]


def build(
    category_name_common,
    subsidary_cd,
    yymmdd,
    scenario_tag,
    input_rows,
    input_header,
    spec_name_common_rows,
    exception_rows,
    type_match_rows,
    basic_spec_def_rows,
    output_dir="/mnt/user-data/outputs",
):
    if not re.fullmatch(r"\d{6}", yymmdd):
        raise ValueError(f"yymmdd must be 6 digits, got {yymmdd!r}")
    if subsidary_cd not in {"KOR", "MJP", "USA"}:
        raise ValueError(f"subsidary_cd must be KOR/MJP/USA, got {subsidary_cd!r}")
    if exception_rows:
        raise ValueError(
            "exception_rows must be empty per §14 (exception sheet is always header-only). "
            "If you intend to populate it, confirm with the user first — this is a deliberate "
            "deviation from the skill's default convention."
        )
    if not (1 <= len(basic_spec_def_rows) <= 2):
        raise ValueError(
            f"BasicSpecDefenition should have 1-2 rows per §13, got {len(basic_spec_def_rows)}. "
            "If more are genuinely needed, confirm with the user before overriding."
        )

    os.makedirs(output_dir, exist_ok=True)
    input_name, spec_name, type_name = _build_filenames(
        category_name_common, subsidary_cd, yymmdd, scenario_tag
    )
    input_path = os.path.join(output_dir, input_name)
    spec_path = os.path.join(output_dir, spec_name)
    type_path = os.path.join(output_dir, type_name)

    _write_csv_with_bom(input_path, input_header, input_rows)
    _write_xlsx(spec_path, {
        "specNameCommon": (SPEC_NAME_COMMON_HEADER, spec_name_common_rows),
        "exception": (EXCEPTION_HEADER, exception_rows),
    })
    _write_xlsx(type_path, {
        "TypeMatch": (TYPE_MATCH_HEADER, type_match_rows),
        "BasicSpecDefenition": (BASIC_SPEC_DEF_HEADER, basic_spec_def_rows),
    })

    return {
        "paths": {"input": input_path, "spec_grouping": spec_path, "type_grouping": type_path},
        "filenames": {"input": input_name, "spec_grouping": spec_name, "type_grouping": type_name},
    }


def write_doc(path, content, output_dir="/mnt/user-data/outputs"):
    """Write the Test Scenarios doc (plain markdown).
    Claude composes the markdown content; this just writes it consistently."""
    os.makedirs(output_dir, exist_ok=True)
    full_path = os.path.join(output_dir, path) if not os.path.isabs(path) else path
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    return full_path


def doc_filenames(category_name_common, yymmdd, scenario_tag):
    """Test Scenarios doc file name - reference-only, not uploaded to S3, so no need
    to match the pipeline naming validator, but kept in the same family for consistency."""
    cat = _category_to_filename_segment(category_name_common)
    tag = f"_{scenario_tag}" if scenario_tag else ""
    scenarios_name = f"TestScenarios_{cat}_{yymmdd}_TestFile{tag}.md"
    return scenarios_name


# --- Discontinued DB (DDB) file (test_run_conventions.md §16) -----------------

DDB_PREFIX = "JIRA-DDB-"
DISCONTINUED_FIXED_HEADER = [
    "discontinued_part_number", "discontinued_part_number_type",
    "category_name_original_en", "category_name_original", "category_name_common",
    "brand_name_original_en", "brand_name_original", "brand_name_common",
    "subsidary_cd", "discontinued_params",
]


def discontinued_header(n_slots):
    """10 fixed columns + (recommend_part_number_n, recommend_part_number_type_n,
    recommend_params_n) for n = 1..n_slots  ->  10 + 3N columns."""
    header = list(DISCONTINUED_FIXED_HEADER)
    for n in range(1, n_slots + 1):
        header += [f"recommend_part_number_{n}", f"recommend_part_number_type_{n}", f"recommend_params_{n}"]
    return header


def discontinued_filename(category_name_common, subsidary_cd, yymmdd, scenario_tag):
    """'Discontinued_<CAT>_<SUB>_TestFile_<YYMMDD>_<tag>.csv'. The tag (1-2 word test
    nature) is mandatory here and is the same scenario tag used on the other files."""
    if not scenario_tag:
        raise ValueError("Discontinued file requires a scenario tag (1-2 word test nature), e.g. 'replacement_chain'")
    cat = _category_to_filename_segment(category_name_common)
    return f"Discontinued_{cat}_{subsidary_cd}_TestFile_{yymmdd}_{scenario_tag}.csv"


def build_discontinued(
    input_rows,
    recommendations,
    category_name_common,
    subsidary_cd,
    yymmdd,
    scenario_tag,
    n_slots=3,
    output_dir="/mnt/user-data/outputs",
):
    """Write the Discontinued CSV, derived entirely from the Input GDB rows.

    recommendations: ordered dict {ddb_part_number: [normal_part_number, ...]} — one
    key per JIRA-DDB- row in input_rows; an empty list means "no alternative".
    Every value (types, category/brand, params) is looked up from input_rows, so
    nothing is re-typed; *_en columns copy the matching *_original value.
    """
    if not re.fullmatch(r"\d{6}", yymmdd):
        raise ValueError(f"yymmdd must be 6 digits, got {yymmdd!r}")
    if n_slots < 1:
        raise ValueError(f"n_slots must be >= 1, got {n_slots}")

    by_pn = {row["part_number"]: row for row in input_rows}
    gdb_ddb = [pn for pn in by_pn if pn.startswith(DDB_PREFIX)]
    missing = [pn for pn in gdb_ddb if pn not in recommendations]
    if missing:
        raise ValueError(f"DDB row(s) in the GDB have no entry in recommendations: {missing}")

    rows = []
    for ddb_pn, recs in recommendations.items():
        if not ddb_pn.startswith(DDB_PREFIX):
            raise ValueError(f"{ddb_pn!r} is not a DDB part number (must start with {DDB_PREFIX})")
        src = by_pn.get(ddb_pn)
        if src is None:
            raise ValueError(f"discontinued part number {ddb_pn!r} not found in the GDB rows")
        if len(recs) > n_slots:
            raise ValueError(f"{ddb_pn!r} has {len(recs)} recommendations but n_slots={n_slots}")
        if len(set(recs)) != len(recs):
            raise ValueError(f"{ddb_pn!r} repeats a recommended part number: {recs}")

        out = {
            "discontinued_part_number": ddb_pn,
            "discontinued_part_number_type": src["part_number_type"],
            "category_name_original_en": src["category_name_original"],
            "category_name_original": src["category_name_original"],
            "category_name_common": src["category_name_common"],
            "brand_name_original_en": src["brand_name_original"],
            "brand_name_original": src["brand_name_original"],
            "brand_name_common": src["brand_name_common"],
            "subsidary_cd": src["subsidary_cd"],
            "discontinued_params": src.get("params", ""),
        }
        for n, rec_pn in enumerate(recs, start=1):
            rec = by_pn.get(rec_pn)
            if rec is None:
                raise ValueError(f"recommended part number {rec_pn!r} (for {ddb_pn!r}) not found in the GDB rows")
            if rec_pn.startswith(DDB_PREFIX):
                raise ValueError(f"recommended part number {rec_pn!r} (for {ddb_pn!r}) is itself a DDB row")
            out[f"recommend_part_number_{n}"] = rec_pn
            out[f"recommend_part_number_type_{n}"] = rec["part_number_type"]
            out[f"recommend_params_{n}"] = rec.get("params", "")
        rows.append(out)

    os.makedirs(output_dir, exist_ok=True)
    name = discontinued_filename(category_name_common, subsidary_cd, yymmdd, scenario_tag)
    path = os.path.join(output_dir, name)
    _write_csv_with_bom(path, discontinued_header(n_slots), rows)
    return {"path": path, "filename": name}

