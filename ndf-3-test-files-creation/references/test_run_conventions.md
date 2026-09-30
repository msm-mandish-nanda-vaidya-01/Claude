# ETL Test Run Conventions

These conventions govern how the 3 files are named and how key fields are derived, so the pipeline can route/process them correctly. Apply these alongside `validation_rules.md` — this file governs naming/derivation, the other governs per-field validation. Everything below has been cross-checked against a real reference set (JIRA-1761, subsidiary MJP) and corrected accordingly — treat this file as authoritative over any conflicting generic example.

## 1. Files Required for a Test Run

Every ETL test requires exactly three files:

| File | Format | Purpose | Upload destination |
|---|---|---|---|
| **Input File** | `.csv` | Contains the parts data — part numbers, categories, brands, subsidiary codes | S3 Explorer → `gdb_registration` |
| **Spec Grouping File** | `.xlsx` | Defines the specification groups for the category | S3 Explorer → `normalisation_master` |
| **Type Grouping File** | `.xlsx` | Defines the type groups for the category | S3 Explorer → `requirement_master` |

All three files must use the same `category_name_common` in their file names. They are processed together by the pipeline.

**DDB mode (on request only):** a fourth pipeline file, the **Discontinued** CSV, is added when the user says the ticket is for the DDB (discontinued database). It is derived from the Input CSV — see §16.

## 2. Category Name Convention

The category name is derived directly from the Jira ticket number, to ensure uniqueness across all test files.

**Format:** `JIR A<first digit> <last 3 digits>` — e.g. ticket `1761` → `JIR A1 761`.

**Rules:**
- `category_name_common` and `category_name_original` must be **identical**.
- Do not use hyphens or underscores inside the category name itself (underscores only appear later, in file names).

**Examples:**

| Jira Ticket | category_name_common | category_name_original |
|---|---|---|
| NDFDPAPJ-1636 | `JIR A1 636` | `JIR A1 636` |
| NDFDPAPJ-1363 | `JIR A1 363` | `JIR A1 363` |
| NDFDPAPJ-2001 | `JIR A2 001` | `JIR A2 001` |
| NDFDPAPJ-1761 | `JIR A1 761` | `JIR A1 761` |

## 3. Part Number Convention

Part numbers are tied to the Jira ticket number and the sequential row number. **Parameter icons are optional** — only append them when that row's `part_number_rules`/`params` actually define parameterized values.

**Format (with icons):** `JIRA-<ticket>-<NN>-<icon1>-<icon2>-...-<iconM>`
**Format (without icons):** `JIRA-<ticket>-<NN>` (plain, no icon suffix)

**Rules:**
- `<NN>` always starts at `01`, increments sequentially, zero-padded two digits (`01`, `02`, ..., `09`, `10`, `11`, ...). Never skip numbers; never reuse a part number from a different ticket.
- **Icons, `params`, and `part_number_rules` are all optional and travel together**: if a row has no parameterized values, its `part_number` has no icon suffix, `params` is empty, and `part_number_rules` is empty.
- **Two kinds of icon, when a row does use parameters** (full rule in §3a):
  - **Selectable icons** — chosen by the customer, and the only ones that appear in the `part_number` icon suffix (consecutive, starting at ①, no gaps).
  - **Derived icons** — may be defined in `params` too, but are deliberately left OUT of the `part_number` icon suffix because the system assigns their value automatically via `part_number_rules` instead of the customer picking it.
  - `part_number`'s icon suffix therefore no longer has to mirror `params` icon-for-icon — it only contains the selectable ones. A row can have selectable icons only, or selectable + derived.
- `part_number_rules` is **optional** for a row with only selectable icons and no conditional logic to express. It becomes **mandatory** the moment a row defines any derived icon — a derived icon has to get its value from somewhere, and `part_number_rules` is that somewhere (§3a).
- The number of icons varies row to row depending on how many parameters that part number needs — it is NOT fixed across the file.

**Examples (with icons, ticket NDFDPAPJ-1761):**
- `JIRA-1761-01-①-②-③` (3 selectable params, no derived params)
- `JIRA-1761-09-①-②-③-④-⑤-⑥-⑦-⑧-⑨-⑩` (10 selectable params)

**Example (without icons, ticket NDFDPAPJ-1457):**
- `JIRA-1457-01` (no params, no rules — plain part number, `params` and `part_number_rules` columns left empty)

**DDB mode:** discontinued rows use `JIRA-DDB-<ticket>-<NN>[-<icons>]` instead; `<NN>` is shared with the normal rows' sequence (§16).

## 3a. Selectable vs. Derived Params (icons defined in `params` but not in the part number)

When `params` defines an icon that does NOT appear in the `part_number` icon suffix, that icon is **derived**: the customer has no slot to pick it from in the printed part number, so the system must compute/assign its value automatically instead. This changes four things versus a row with only selectable icons:

1. **One consecutive icon sequence, no gaps, across selectable + derived combined.** E.g. a part number with 3 selectable icons (①②③) that also needs 2 derived icons uses ④ and ⑤ for those — never restart at ①, never skip a number.
2. **Ordering inside the `params` cell: selectable icons must be defined first, in order, then derived icons after them.** Don't interleave. E.g. `①[...],②[...],③[...],④[...],⑤[...]` (①②③ selectable, ④⑤ derived) — never `①[...],④[...],②[...]`.
3. **`+`/`-` restriction, split by icon kind:**
   - A **selectable** icon's defined values must NOT contain `+` or `-` — these values get substituted straight into the customer-facing part number, and a `+`/`-` there would be ambiguous or break parsing. For a value-list/irregular block this means neither side of any `key=value` pair may contain `+`/`-`. For a range block it means `min` must be `>= 0` (a negative min would let the customer land on a `-`-containing resolved value).
   - A **derived** icon's defined values MAY contain `+`/`-` freely (e.g. `+5%`, `-5%`, negative range bounds) — they're never substituted into a printed slot the same way, so there's no parsing conflict.
4. **Every derived icon must be assigned by `part_number_rules`, and every value it defines must be reachable.** `part_number_rules` needs enough `IF [...] Rule <derived_icon>=<value>;` branches (conditioned on the selectable icons) that each value listed for that derived icon actually gets produced by at least one branch. A value sitting in a derived icon's `params` list that no rule branch ever assigns is a dead value — the pipeline can define it but the customer can never actually reach it.

See §8 for the exact `part_number_rules` syntax used to express derived-icon assignment, including a worked example.

## 4. Part Number Type Convention

The part number type is just the ticket-independent, icon-independent sequence suffix — it does NOT include the ticket segment or the parameter icons.

**Format:** `JIRA-01`, `JIRA-02`, ... `JIRA-0N`

| Part Number | Part Number Type |
|---|---|
| `JIRA-1761-01-①-②-③` | `JIRA-01` |
| `JIRA-1761-06-①-②-③-④-⑤-⑥-⑦-⑧-⑨` | `JIRA-06` |
| `JIRA-1761-09-①-②-③-④-⑤-⑥-⑦-⑧-⑨-⑩` | `JIRA-09` |

## 5. Subsidiary Code Convention

`subsidary_cd` (note: this field name is spelled without the second "i" throughout the actual schema — `subsidary_cd`, not `subsidiary_cd`) must be one of: **`KOR`, `MJP`, `USA`** — this is the authoritative enum (matches `validation_rules.xlsx`; MJP is confirmed by real reference files). Do not use `JPN` or `TWN` as substitutes for Japan — `MJP` is the correct code.

## 6. File Naming Convention

File names encode category, subsidiary code, date, and an optional free-text scenario tag. Follow the format exactly — the pipeline parses file names to route and process files, and **fails silently** if the pattern doesn't match.

- **Input File:** `Input_<category_name_common>_<subsidary_cd>_TestFile_<YYMMDD>[_<scenario_tag>].csv`
  Example: `Input_JIR_A1_761_MJP_TestFile_260707_and_or.csv`
- **Spec Grouping File:** `SpecGrouping_<category_name_common>_<YYMMDD>_TestFile[_<scenario_tag>].xlsx`
  Example: `SpecGrouping_JIR_A1_761_260707_TestFile_and_or.xlsx`
- **Type Grouping File:** `TypeGrouping_<category_name_common>_<YYMMDD>_TestFile[_<scenario_tag>].xlsx`
  Example: `TypeGrouping_JIR_A1_761_260707_TestFile_and_or.xlsx`

**Field reference:**

| Field | Format | Example |
|---|---|---|
| `category_name_common` | Words from category name joined by underscores | `JIR_A1_761` |
| `subsidary_cd` | One of `KOR`, `MJP`, `USA` (see section 5) | `MJP` |
| date | `YYMMDD` (2-digit year, 2-digit month, 2-digit day) — **not** `YYYYMMDD` | `260707` (2026-07-07) |
| `scenario_tag` | Optional free-text suffix (see section 7) describing the test scenario, appended to all 3 file names identically | `and_or` |

**Key notes:**
- Spaces in the category name become underscores in the file name (`JIR A1 761` → `JIR_A1_761`).
- Always include `TestFile` in the name — this distinguishes test files from production data.
- The date is `YYMMDD` (6 digits), matching the file-name pattern rule in `validation_rules.md` itself — not the 8-digit `YYYYMMDD` used in an earlier draft of this doc. Use `YYMMDD` going forward.
- Maintain exact formatting; a mismatched pattern causes a silent pipeline failure, not an error.
- **Preserve exact case and use underscores, never spaces, in the actual file name.** File names must look like `Input_JIR_A1_457_KOR_TestFile_260721.csv` — segments joined by underscores, category words and codes kept in their original case. Do NOT lowercase the name or join it with spaces (e.g. `jir a1 457 mjp testfile 260721` is wrong on multiple counts: wrong case, wrong separator, and it must be an actual mistake, not a stylistic choice).
- **Use the subsidiary code the user actually specified/confirmed for this test run** in the file name — never substitute a different or default subsidiary code than the one established in step 3 of the workflow.

## 7. Scenario Tag Convention (optional suffix)

When a test run is built around a specific testing scenario (e.g. exercising AND/OR logic in `part_number_rules`, or some other targeted validator behavior), append a short free-text scenario tag to the end of **all three** file names, identically, after `TestFile`. This is optional — omit it for a plain/generic test set.

- Keep it short, lowercase, underscore-separated (e.g. `and_or`, `range_check`, `icon_gaps`).
- It must appear on all 3 files consistently — mismatched tags across the 3 files break the "files belong to the same test run" assumption the pipeline relies on.
- If the user describes a scenario/purpose for the test files (e.g. "test AND/OR rule logic"), proactively propose a matching scenario tag rather than defaulting to no tag.

## 8. Part Number Rules Logic (AND/OR, and Derived-Icon Assignment)

`part_number_rules` lines may combine `AND` and `OR` connectors within both the IF-condition and the Rule-consequent — this is valid, not just a single flat condition:

- **In the IF-condition:** `IF [③=high grade OR ③=precision grade] Rule 110<=②<=2000;` or `IF [④=ABC AND ⑤!=-] Rule ⑦=- AND ⑧=-;`
- **In the Rule-consequent:** `Rule ②!=長16m AND ②!=長17m AND ②!=長18m AND ②!=ロ16m AND ②!=ロ17m AND ②!=ロ18m;`
- Every line must still start with `IF` (optional) or `Rule` (mandatory) and end with `;`, per `validation_rules.md`. The `IF [...]` block, when present, comes before `Rule`, and both the condition inside `[...]` and the consequent after `Rule` may chain multiple `AND`/`OR` comparisons.
- **When a line has an `IF [...]` condition, the first parameter icon referenced must exist in the `part_number` column** — i.e. conditions branch on selectable icons (per `validation_rules.md`'s `PartNumberRulesParamSequenceCheck`). The `Rule` consequent is where a derived icon (§3a) gets targeted instead — e.g. in `IF [④=ABC AND ⑤!=-] Rule ⑦=- AND ⑧=-;`, ④ is the selectable icon driving the condition, while ⑦/⑧ are derived icons being assigned the value `-` (only legal for derived icons, since selectable icons can't carry `-` in their values, per §3a).
- **Derived-icon assignment:** a derived icon gets its value exclusively through `Rule <derived_icon>=<value>;` lines, almost always behind an `IF [...]` branch on one or more selectable icons. A row with a single-valued derived icon can use one unconditional `Rule <derived_icon>=<value>;` line instead (no `IF` needed) — in that case the derived icon itself is the line's first (and only) icon, which is fine precisely because there's no condition to branch on.
- **Reachability:** every value listed in a derived icon's `params` block must be produced by at least one `part_number_rules` branch. For a derived icon with N possible values, that typically means N separate `IF [...] Rule <derived_icon>=<value_n>;` lines (one per value), each keyed off a different selectable-icon condition — not just one branch that only ever reaches one of the values.

**Worked example — derived icon assignment (selectable ①②, derived ③ with values `positive`/`negative`):**
```
IF [①=A] Rule ③=positive;
IF [①=B] Rule ③=negative;
```
Both values defined for ③ in `params` are reachable — one via `①=A`, the other via `①=B`. A file that only ever wrote the first line would leave `negative` unreachable and fail the reachability check.

## 9. Input File Structure (minimum required columns)

| Column | Description | Example |
|---|---|---|
| `part_number` | Full part number including icon suffix (see section 3) | `JIRA-1761-01-①-②-③` |
| `part_number_type` | Part number type suffix, no ticket/icons (see section 4) | `JIRA-01` |
| `category_name_common` | Category name (same as `category_name_original`) | `JIR A1 761` |
| `category_name_original` | Category name (same as `category_name_common`) | `JIR A1 761` |
| `brand_name_common` | Brand name (use `MISUMI` for test data) | `MISUMI` |
| `brand_name_original` | Brand name (same as `brand_name_common`) | `MISUMI` |
| `subsidary_cd` | Subsidiary code, see section 5 | `MJP` |

These columns are in addition to (not a replacement for) the full required-column list in `validation_rules.md` (spec_type_1..N, params, part_number_rules, economy_flag, etc.) — merge both lists when building the CSV.

**Example rows (ticket NDFDPAPJ-1761, MJP subsidiary):**

| part_number | part_number_type | category_name_common | category_name_original | brand_name_common | brand_name_original | subsidary_cd |
|---|---|---|---|---|---|---|
| JIRA-1761-01-①-②-③ | JIRA-01 | JIR A1 761 | JIR A1 761 | MISUMI | MISUMI | MJP |
| JIRA-1761-02-①-②-③ | JIRA-02 | JIR A1 761 | JIR A1 761 | MISUMI | MISUMI | MJP |
| JIRA-1761-06-①-②-③-④-⑤-⑥-⑦-⑧-⑨ | JIRA-06 | JIR A1 761 | JIR A1 761 | MISUMI | MISUMI | MJP |

## 10. Params Value-List Convention (test-data pattern)

For `irregular`/formula-style params with an explicit value list (e.g. `③[h=high grade,p=precision grade,XYZ=XYZ]`), it's standard practice in these test files to include a trailing catch-all pair `XYZ=XYZ` in each icon's value list. This represents a deliberate "non-matching / unmapped" value for negative-path testing (a value that doesn't satisfy any of the named rule conditions). Include this catch-all by default when generating irregular-type params with explicit value lists, unless the user says otherwise.

## 11. Spec Grouping File — `exception` Sheet

The `exception` sheet must exist with its correct header row — columns `#, subsidary_cd, part_number_type, brand_name_common, category_name_common, spec_name_common, stringReplacement, calculationFormula, unitConversionFormula` (note `part_number_type` sits between `subsidary_cd` and `brand_name_common`). For this skill's default output, treat it as **always empty** (zero data rows) — see §14 for the full always-empty-fields convention.

## 12. Type Grouping File — `TypeMatch` Brand Convention

`TypeMatch`'s `brand_name_common` is **one fixed "primary" brand for the entire file**, regardless of what individual brands appear per-row in the Input CSV. Even if the CSV mixes multiple brands across rows (e.g. some rows `MISUMI`, others `ABC`), `TypeMatch` still lists the same single chosen primary brand (typically `MISUMI` for test data) against every `part_number_type`. Do not try to mirror each row's actual brand here.

## 13. Type Grouping File — `BasicSpecDefenition` Scope

`BasicSpecDefenition` is a **matching-logic hint list**, not a full listing of every spec used in the Input CSV, and not necessarily every spec common to every row either. For simplicity, keep it to just **1–2 specs** — preferably whichever spec(s) are common across all part numbers in the file. This is a deliberate simplification for matching logic, not a strict derivation rule: when several specs are common to every row, still pick only 1–2 of them rather than listing all of them. Keep `spec_name_common` unique within the sheet.

By contrast, `TypeMatch` **always** lists every `part_number_type` from the CSV 1:1, with no filtering — one row per part number type, no omissions (using the fixed primary brand from §12, not each row's actual brand).

## 14. Always-Empty Fields Convention

Certain columns/sheets must exist with the correct header, but their values must always be left empty for these generated test files — do not populate them with placeholder or sample data:

- **Input CSV**: `cad_url`, `image_alt`, `image_pass` — these columns must be present in the header row, but every row's value for them stays empty (`''`).
- **Spec Grouping xlsx, `specNameCommon` sheet**: `calculationFormula` — column must exist, default empty. If a row does populate it, the value must follow the strict syntax rules in `validation_rules.md` §2 ("calculationFormula syntax rules") — one of the 5 permitted patterns (CEILING, ROUND, tolerance-range, add/subtract, notation-equality), terminating `;`, correct `RULE`/`AND`/`OR` spacing, and only the allowed operator set. Don't invent a 6th shape or write a real formula outside those patterns.
- **Spec Grouping xlsx, `exception` sheet**: columns are `#, subsidary_cd, part_number_type, brand_name_common, category_name_common, spec_name_common, stringReplacement, calculationFormula, unitConversionFormula` — the sheet and its header row must exist with this exact column set/order, but it always has **zero data rows** (headers only, no exceptions populated), regardless of scenario. This supersedes the earlier "may be left empty unless the scenario calls for an exception case" framing in §11 — for this skill's purposes, `exception` is always empty.

These are separate from the null-check validators in `validation_rules.md` — those columns aren't in the non-null required list, so leaving them empty is valid, not a validator violation.

## 15. CSV Encoding (UTF-8 with BOM)

The Input CSV must be written as **UTF-8 with a BOM** (byte order mark), i.e. what Excel calls "CSV UTF-8 (Comma delimited) (*.csv)" — not plain UTF-8. The reference file for JIRA-1761 confirms this: its first bytes are `EF BB BF` (the UTF-8 BOM) before `part_number,...`.

Without the BOM, Excel opens the CSV using the system's local codepage instead of UTF-8, and any Japanese (or other non-ASCII) text in columns like `spec_name_original_*`/`spec_name_common_*` renders as mojibake/garbled characters, even though the underlying file is valid UTF-8.

**When writing the CSV in Python**, use `encoding='utf-8-sig'` (not `'utf-8'`) so the BOM is included:
```python
with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f)
    ...
```
Verify the BOM is present by checking that the file's first 3 bytes are `EF BB BF` before finalizing.

## 16. Discontinued DB (DDB) Mode — Discontinued Input File (on request only)

**Trigger:** generate only when the user explicitly says the ticket is for the DDB (discontinued database) / asks for a Discontinued file. It is derived from the Input GDB CSV built in the same run — the GDB CSV must exist first.

**File name:** `Discontinued_<category_name_common>_<subsidary_cd>_TestFile_<YYMMDD>_<scenario_tag>.csv`
Example: `Discontinued_JIR_A2_285_MJP_TestFile_260930_replacement_chain.csv`
- Category underscore-joined, 6-digit `YYMMDD`, same case rules as §6.
- In DDB mode the scenario tag (§7) is **mandatory**: it is the 1–2 word test nature, and the same tag is appended to all other files in the run (Input, SpecGrouping, TypeGrouping, TestScenarios).

**S3 upload destination:** not yet defined (TODO — confirm with the team). Tell the user this rather than guessing.

### Step 1 — Input GDB CSV in DDB mode (10 rows by default)

- **4 DDB rows + 6 normal rows**, numbered `NN = 01..10` in one sequence, with the DDB rows mixed in (not grouped at the end).
- DDB row `part_number`: `JIRA-DDB-<ticket>-<NN>`, plus the icon suffix when it has params (e.g. `JIRA-DDB-2285-04-①-②`). Normal rows keep `JIRA-<ticket>-<NN>[-icons]` (§3).
- `part_number_type` stays `JIRA-<NN>` for **every** row, DDB or not (§4). `TypeMatch` therefore lists all 10 types.
- DDB rows are ordinary GDB rows — they must pass every existing GDB validator (icons, params, rules, spec types, etc.).
- Minimums: among the DDB rows at least **1 plain** and **2 icon-bearing**; at least **3 normal rows** so every recommendation slot can be filled.

### Step 2 — Discontinued file

**Header:** the 10 fixed columns, then `recommend_part_number_n, recommend_part_number_type_n, recommend_params_n` for `n = 1..N`.

Fixed columns (in order): `discontinued_part_number, discontinued_part_number_type, category_name_original_en, category_name_original, category_name_common, brand_name_original_en, brand_name_original, brand_name_common, subsidary_cd, discontinued_params`

Default `N = 3` → 19 columns. If the user asks for more recommendations, N grows: column count = `10 + 3N`.

**Rows:** exactly one per DDB part number; no rows for normal part numbers.

**Values** — everything is read from the part number's GDB row:

| Discontinued column | Source (GDB row of the discontinued pn) |
|---|---|
| `discontinued_part_number` | `part_number` |
| `discontinued_part_number_type` | `part_number_type` |
| `category_name_original_en` | `category_name_original` (GDB has no `_en` source) |
| `category_name_original` / `category_name_common` | same-named GDB columns |
| `brand_name_original_en` | `brand_name_original` (GDB has no `_en` source) |
| `brand_name_original` / `brand_name_common` / `subsidary_cd` | same-named GDB columns |
| `discontinued_params` | `params`, copied unchanged (ranges, key=value lists, plain lists like `①[10,20,30]` all allowed) |
| `recommend_part_number_n` / `_type_n` / `recommend_params_n` | `part_number` / `part_number_type` / `params` of the recommended **normal** GDB row |

- Icons keep the GDB format `-①-②` (not the `-①②` form seen in an older reference), because values are copied from the GDB.
- Slots fill left to right. A slot is *filled* when its part number and type are set; `recommend_params_n` is then the GDB params as-is — it may be empty when the recommended row is plain. An empty slot has all 3 cells empty.
- A recommendation always points at a normal (non-DDB) row; a DDB row is never recommended. No part number repeats within one row.
- Encoding: UTF-8 with BOM (§15), standard CSV quoting.

**Default shapes for the 4 DDB rows:**

| DDB row | Recommendations |
|---|---|
| Plain | none (no alternative) |
| Plain | 1 |
| Icon | 2 |
| Icon | 3 (this row sets N = 3) |

Reuse at least one normal part number across two DDB rows (e.g. the same normal pn in the 2-rec and 3-rec rows).

**Test Scenarios doc:** add a table mapping each DDB row → plain / icon-bearing → shape (0/1/2/3 recs) → recommended part numbers.
