# NDF Validation Rules Reference

Extracted from `validation_rules.xlsx`. Three registries, each backing one of the three output files.

---

## 1. InputSheet (GDB CSV)

**File name pattern:** `Input_Category_<anything>_YYMMDD_<anything>.csv`
**Format:** valid UTF-8 CSV

**Required columns (must all be present, unique, in this order is not mandatory but presence is):**
```
part_number, part_number_type, category_name_original, category_name_common,
brand_name_original, brand_name_common, subsidary_cd, part_number_rules,
params, series_name, cad_url, image_alt, image_pass, economy_flag,
spec_type_1, spec_name_original_1, spec_name_common_1, spec_value_1, spec_unit_1
```
- At least one complete spec column set (`spec_type_N ... spec_unit_N`) is required; additional sets (N=2, N=3, ...) must each be complete if present.

**Non-null columns:** part_number, part_number_type, category_name_original, category_name_common, brand_name_original, brand_name_common, subsidary_cd, economy_flag, spec_type_1, spec_name_original_1, spec_name_common_1, spec_value_1, spec_unit_1

**Row rules:**
- No leading/trailing/consecutive spaces in any cell.
- No duplicate rows.

**Data rules:**
- `subsidary_cd` ∈ {KOR, MJP, USA}.
- `category_name_common` must be a single consistent value across all rows in the file.
- `spec_type_*` ∈ {fixed, irregular, range, formula}.
- `spec_name_common_*` must not contain "/".
- `spec_value_*` must not contain "," or lowercase "φ".
- `economy_flag` ∈ {0, 1}.
- `params` pattern: `①[value list], ②[range]` etc. Value list = `[value1=value1, value2=value2]` or `[start-end/step]`. Range = `[min-max/step]`. Numeric validity: min < max, step > 0.
- `part_number_rules`: every line starts with "If" (optional) or "Rule" (mandatory) and ends with ";".
- `spec_type` / `spec_value` / `params` cross-check:
  - fixed → spec_value must NOT be a parameter icon (①②③...).
  - formula → spec_value must contain ≥1 parameter icon, every icon used must be defined in params.
  - range → spec_value must be exactly one parameter icon, defined in params, whose block matches `min-max/step` (non-zero step).
  - irregular → spec_value must be exactly one parameter icon, defined in params, whose block matches key=value pairs or a comma-separated list.
- Parameter icon consistency across part_number, part_number_rules, params, spec_value_1..N:
  - Icons defined in params must appear in some spec_value.
  - Icons used in part_number/part_number_rules must be defined in params.
  - Icons in part_number ("selectable" icons) must be consecutive starting at ① with no gaps.
  - `params` may also define icons that do NOT appear in part_number ("derived" icons — see below). Combining selectable + derived, the full icon set defined in `params` must still be one consecutive run starting at ①, with no gaps.
  - Within the `params` cell, selectable icons must be defined first (in order), followed by any derived icons — no interleaving.
- Selectable vs. derived icon value restriction (test_run_conventions.md §3a):
  - A selectable icon's values must NOT contain `+` or `-`: neither side of a `key=value` pair in a value-list/irregular block, and a range block's `min` must be `>= 0`.
  - A derived icon's values MAY contain `+` or `-` freely (e.g. `+5%`, `-5%`, negative range bounds).
- Derived icon assignment / reachability (test_run_conventions.md §8):
  - Every derived icon must be assigned by at least one `part_number_rules` line (`Rule <icon>=<value>;`).
  - Every value defined for a derived icon in `params` must be produced by at least one rule branch — a defined value with no reachable rule branch is an error.
- First parameter icon referenced in a part_number_rules line's `IF [...]` condition must exist in the part_number column (conditions branch on selectable icons only). A line with no `IF` condition — a bare `Rule <derived_icon>=<value>;` — may have a derived icon as its first/only icon instead, since there's no condition to branch on.

---

## 2. Spec_Grouping (xlsx)

**File name pattern:** `SpecGrouping_Category_<text>_YYMMDD_<text>.xlsx`
**Required sheets:** `specNameCommon`, `exception`

**specNameCommon columns:**
```
#, subsidary_cd, category_name_common, spec_name_common,
stringReplacement, calculationFormula, unitConversionFormula,
exceptionBt_no, priority_order
```

**exception columns:**
```
#, subsidary_cd, part_number_type, brand_name_common, category_name_common, spec_name_common,
stringReplacement, calculationFormula, unitConversionFormula
```

**Row rules:** no leading/trailing/consecutive spaces; no duplicate rows.
**Structure:** headers in each sheet must exactly match the lists above (case-insensitive sheet-name matching).

**Data rules:**
- `subsidary_cd` ∈ {KOR, MJP, USA}.
- `category_name_common` single consistent value across all rows.
- `spec_name_common` unique within each sheet.
- `stringReplacement` format: `[["value_1","value_2"],["value_3","value_4"]]`. A value must not appear in more than one replacement group for the same `spec_name_common`.
- Required columns (#, subsidary_cd, category_name_common, spec_name_common, priority_order) cannot be null.
- `category_name_common` must match the InputSheet CSV(s).
- `spec_name_common` values must exist in the reference InputSheet CSV(s) (i.e. must match a `spec_name_common_*` value there).
- `subsidary_cd` must be consistent across all files (InputSheet, Spec_Grouping, Type_Grouping).
- `priority_order` unique within the `specNameCommon` sheet.
- `calculationFormula` in `specNameCommon`: default empty. If populated, it must comply with the syntax rules in "calculationFormula syntax rules" below — anything that doesn't match is a validator error, not a warning.

### calculationFormula syntax rules

These apply only when `calculationFormula` is non-empty for a row.

- Must end with a semicolon (`;`).
- If multiple conditions/statements are listed in one cell, each one ends with `;` followed by a line break (`\n`) — one statement per line, every line semicolon-terminated.
- Half-width (ASCII) spaces must surround `RULE`, `AND`, and `OR` on both sides — no full-width spaces, no missing spaces, no tabs.
- Allowed operators/tokens only: `<=`, `>=`, `<`, `>`, `=`, `!=`, `*`, `+`, `-`, `%`, `/`, `AND`, `OR`. Anything else (`==`, `<>`, `&&`, `||`, etc.) is invalid.
- Every statement must match exactly one of these 5 patterns (`spec_name_common` here is literal — it is not replaced with the row's actual spec name):
  1. **CEILING** (round up to multiple): `IF [spec_name_common<=10 AND spec_name_common%1 !=0] RULE CEILING(spec_name_common, 1);`
  2. **ROUND** (round to nearest): `IF [spec_name_common > 0] RULE ROUND(spec_name_common,5);`
  3. **Equality check within tolerance range**: `spec_name_common+10%;` / `spec_name_common-10%;` / `spec_name_common±10%;` — `±` is valid **only** in this pattern, nowhere else.
  4. **Addition/subtraction of spec values**: `spec_name_common+3;` / `spec_name_common-3;`
  5. **Equality check for notation variations**: `IF [spec_name_common=A] RULE spec_name_common=B;`
- Any statement that doesn't fit one of these 5 shapes, uses a disallowed operator, is missing its terminating `;`, is missing a required space around `RULE`/`AND`/`OR`, or uses `±` outside pattern 3, is a validator **error**.

---

## 3. Type_Grouping (xlsx)

**File name pattern:** `TypeGrouping_Category_<text>_YYMMDD_<text>.xlsx` (or `Type_Grouping*.xlsx`)
**Required sheets:** `TypeMatch`, `BasicSpecDefenition`

**TypeMatch columns:**
```
#, subsidary_cd, category_name_common, brand_name_common, part_number_type
```

**BasicSpecDefenition columns:**
```
#, subsidary_cd, category_name_common, spec_name_common
```

**Row rules:** no leading/trailing/consecutive spaces; no duplicate rows.
**Structure:** headers in each sheet must exactly match the lists above.

**Data rules:**
- `subsidary_cd` ∈ {KOR, MJP, USA}.
- `category_name_common` single consistent value across all rows.
- `spec_name_common` unique within `BasicSpecDefenition`.
- (`part_number_type`, `brand_name_common`) combination unique within `TypeMatch`.
- Required columns cannot be null.
- `category_name_common` must match the InputSheet CSV(s).
- `spec_name_common` in `BasicSpecDefenition` must exist in the reference InputSheet CSV(s).
- (`part_number_type`, `brand_name_common`) pairs in `TypeMatch` must exist in the reference InputSheet CSV(s).
- `subsidary_cd` must be consistent across all files.

---

## Cross-file consistency checklist (applies across all 3 files together)

When generating the 3 files as one linked set, they must agree on:
- `subsidary_cd` — same value(s) used everywhere.
- `category_name_common` — identical single value across all three files.
- `brand_name_common` — values used in Spec_Grouping's `exception` sheet and Type_Grouping's `TypeMatch` sheet must exist in the InputSheet CSV.
- `spec_name_common_*` (InputSheet) ↔ `spec_name_common` (Spec_Grouping's both sheets, Type_Grouping's `BasicSpecDefenition`) — every spec name referenced in the xlsx files must actually appear as a `spec_name_common_N` value in the CSV.
- `part_number_type` (InputSheet) ↔ `part_number_type` (Type_Grouping `TypeMatch`) — every (part_number_type, brand_name_common) pair in TypeMatch must exist in the CSV.

---

## 4. Discontinued file (DDB mode only — test_run_conventions.md §16)

**File name pattern:** `Discontinued_<category>_<subsidary_cd>_TestFile_<YYMMDD>_<scenario_tag>.csv`
**Format:** UTF-8 CSV **with BOM**, standard CSV quoting.

**Structure:**
- Header is exactly the 10 fixed columns `discontinued_part_number, discontinued_part_number_type, category_name_original_en, category_name_original, category_name_common, brand_name_original_en, brand_name_original, brand_name_common, subsidary_cd, discontinued_params`, followed by complete, contiguous triples `recommend_part_number_n, recommend_part_number_type_n, recommend_params_n` for n = 1..N (N ≥ 1).

**Row / data rules:**
- One row per DDB (`JIRA-DDB-`) part number in the Input CSV — none missing, none duplicated.
- Every discontinued and recommended part number exists in the Input CSV.
- No normal row is listed as discontinued; no DDB row is recommended.
- Slots fill left to right; each slot is fully filled (part number + type, params = GDB params, possibly empty) or fully empty.
- No recommended part number repeats within a row.
- Every copied field equals the GDB row's value, including params (`_en` columns equal their `*_original` GDB value).

**Cross-file (extends the checklist above):** every discontinued/recommended part number exists in the Input CSV, and the recommended type/params match that row.
