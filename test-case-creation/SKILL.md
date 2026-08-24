---
name: test-case-creation
description: Generate a QA test case Excel file from a Jira ticket number, its description, an input data sheet, and a test scenarios list. Use whenever the user asks to "create test cases", "write test cases for JIRA-XXXX", "make a test case file", or pastes a Jira ticket/description and wants QA coverage produced, especially for part-number rule/matching tickets (IF-AND, IF-OR, Rule-AND, reverse-implication scenarios) similar to JIRA-1761. Always ask the user for clarification instead of guessing whenever the ticket description is ambiguous, incomplete, or the rule logic/expected behavior isn't fully specified.
---

# Jira Test Case Creation

Generates a test case Excel (.xlsx) file from a Jira ticket + description, an input data sheet, and a test scenarios list, following MISUMI QA standards and the established part-number-rule test case format.

## Required inputs

This skill needs three things from the user before generating test cases. Do not proceed on partial input — ask for whichever of these is missing:

1. **Input sheet** — the actual data file (CSV/Excel) containing the real part numbers, icon/param values, and rule definitions this ticket operates on. Test cases must be derived from this data, not invented values, so that every row uses part numbers/values that actually exist in the dataset.
2. **Test scenarios** — the list of scenario types the user wants covered (e.g. IF-AND, IF-OR, Rule-AND, reverse-implication, regression), or confirmation to use the default scenario set in Step 3 below.
3. **Ticket description** — the Jira ticket number and description, including rule logic, icons/params involved, domain/environment, and subsidiary code.

If the user provides a ticket description but no input sheet, ask them to upload it rather than fabricating sample part numbers. If they provide an input sheet but no explicit scenario list, confirm with them whether to use the default scenario coverage in Step 3, or a custom subset.

## Core principle: ask, don't guess

This is the most important rule in this skill. Test cases are only useful if they reflect real, correct system behavior. If any of the following are unclear from what the user gave you, **stop and ask** (use `ask_user_input_v0` for short, well-defined choices; ask a plain question for open-ended gaps) rather than inventing an answer:

- The exact rule logic (which icons/params are involved, AND vs OR, ranges, reverse-implication direction)
- What counts as a "pass" vs "violation" for a given scenario
- The environment / domain / URL to test against
- Which sheet(s) the ticket needs (FE only, BE only, or both — see below)
- The subsidiary/country code, or whether multiple should be covered
- Whether this is a new-feature ticket, a bug-fix ticket, or a regression pass

Never silently fabricate part number values, rule text, or expected results. If the user's ticket description already contains enough detail to derive these, proceed without asking — only ask about genuine gaps.

## Step 1: Gather ticket context

Collect the three required inputs described above, from the user's message or by asking:

1. **Jira ticket number** (e.g. `JIRA-1761`, `NDFDPAPJ-1757`) and **ticket description** — the feature/bug being tested, ideally including:
   - The part number rule(s) involved, written out precisely (e.g. `IF [③=high grade OR ①=rubber seal] Rule 110<=②<=2000`)
   - Which icons (①②③...) map to which params
   - The domain/environment under test (e.g. `https://stg01.cross-dev.misumi-ec.com/ja/`)
   - The country/subsidiary code (e.g. `MJP`)
2. **Input sheet** — the data file with the actual part numbers/values this ticket applies to. Read it (via `openpyxl`/`pandas`) before generating any rows.
3. **Test scenarios list** — which scenario types the user wants covered (see Step 3), or explicit confirmation to use the default set.
4. **Scope**: is this Frontend behavior (manual search/creation on the website), Backend behavior (API/default-replacement logic), or both?

If the ticket is about part-number rules but the rule logic itself is missing or vague, ask the user to paste or clarify it before generating rows — this is the single most common source of wrong test cases. If the input sheet is missing, ask for it before proceeding — do not generate rows from memory or invented values.

## Step 2: Choose the template

Read `assets/template.xlsx` for the exact column layout and worked examples before writing anything. It has two sheets:

- **FE** — Frontend test cases: manual search/creation of a part number on the website, verifying whether the search is allowed and what validation/recommendation result comes back.
- **BE** — Backend test cases: API-level checks (e.g. whether `default_replacements` is called, whether replacement part numbers share a network number, whether replacement part numbers themselves comply with their own rules).

Columns (identical across both sheets):

| # | Column | Notes |
|---|---|---|
| 1 | SN | Sequential integer per sheet |
| 2 | Date | Date test is (or will be) run |
| 3 | Domain | Exact URL under test |
| 4 | Country | Subsidiary code, e.g. `MJP` |
| 5 | Part Number | Structured part number with icon placeholders, e.g. `JIRA-1761-05-①-②-③` |
| 6 | Part Number Rules | The rule text verbatim, e.g. `IF [110<=②<=2000] Rule ③=high grade AND ①=rubber seal;` |
| 7 | Description | One clear sentence: what scenario this row tests (see scenario types below) |
| 8 | Test Data | Concrete icon→value mapping used for this row, e.g. `①=r, ②=2000, ③=h` |
| 9 | Test Steps | Numbered steps a QA member can follow without asking questions |
| 10 | Expected Result | Specific, single verifiable outcome |
| 11 | Actual Result | Leave identical to Expected Result as a placeholder (filled in for real after running) |
| 12 | OK/NG | Leave blank or `OK` as placeholder — do not fabricate a real test run result |
| 13 | Screenshots | Leave blank — filled in by the tester after running |
| 14 | Comments | Leave blank unless the user gives ticket-specific notes |

If the ticket does not fit the part-number-rule pattern (e.g. it's a dashboard feature, an ETL pipeline change, a validation-tool change), fall back to the general 11-column format in `references/TEST_CASE_STANDARDS.md` instead of forcing the FE/BE layout. Ask the user which format applies if it's not obvious from the ticket description.

## Step 3: Derive scenario coverage from the rule logic, the ticket, and the input data

Test case coverage must satisfy two constraints simultaneously:

1. **Complete against the ticket** — every scenario type mentioned or implied by the ticket description and the user's test scenarios list must be represented at least once. Before building rows, list out every distinct rule/behavior mentioned in the ticket and check off each one as you cover it. If a scenario the user explicitly listed doesn't logically apply to the rule, don't drop it silently — tell the user why it was skipped.
2. **Grounded in the input sheet** — every Part Number / Test Data value used in a row must come from (or be a legitimate boundary derivation of) the input sheet's actual data, not invented. If the input sheet doesn't contain data for a scenario the ticket requires, flag this to the user instead of fabricating a row.

For each distinct rule found in the input sheet / ticket, generate rows covering these scenario types (skip any that don't logically apply, and tell the user which ones you skipped and why):

- **IF-AND**: both conditions true (rule triggers, and check both the "satisfied" and "violated" outcomes); only one condition true (rule does NOT trigger — part stays unconstrained/valid)
- **IF-OR**: each branch tested independently as the sole satisfier; a violation case where the rule triggers but the downstream condition fails
- **Rule-AND** (multiple AND'ed exclusions/conditions on one param): a case where all conditions are simultaneously satisfied; a case where exactly one is broken
- **Reverse-implication** (`IF [range/condition on one icon] Rule [condition on other icons]`): full match; partial match (one sub-condition of the consequent fails)
- **Multi-value OR** (six-plus alternative values): at least one representative branch, plus one violation
- Always include at least one **happy path** and one **violation/error** case per rule; add **edge cases** (boundary values of any numeric range — exactly at min/max, one unit outside) when a range is involved

Cross-check every generated row's Expected Result against the rule text — the logic must be internally consistent (e.g. don't mark something a violation if the AND/OR logic actually says it passes). If you're not fully certain how the system should behave in an edge case, ask the user rather than guessing.

For BE sheet rows, also consider (when the ticket scope includes backend behavior):
- Whether the default-replacement API is called vs not called
- Whether replacement part numbers sharing a network number are consistent
- Whether replacement part numbers themselves satisfy their own rules

### No redundant test case types

Before finalizing the row list, drop rows that are logically duplicate of another row already covering the same (rule + scenario type + pass/fail outcome) combination, even if the underlying part number values differ. Two rows are redundant if they exercise the same branch of the same rule and would produce the same Expected Result via the same logic path — in that case keep only one representative row rather than one per input-sheet value. Only keep multiple rows for the same rule+scenario-type when they test genuinely distinct behavior (e.g. a boundary value vs a mid-range value, or two different violation causes).

## Step 4: Build the file

- Use `openpyxl` to create the workbook, matching the exact column headers, order, and sheet names (`FE`, `BE`, or the general single-sheet format) from the template.
- Number SN sequentially per sheet, starting at 1 unless the user says this continues an existing file (in which case ask for or read the existing file to continue numbering).
- Leave `Actual Result`, `OK/NG`, and `Screenshots` as placeholders as described above — these are meant to be filled in by the QA engineer who actually runs the test, not fabricated by this skill.
- **De-duplicate before writing.** Build the full row list in memory first, then run it through a dedup pass keyed on `(rule_text, scenario_type, expected_result)` — normalize whitespace/case before comparing — and drop repeats, keeping the first occurrence. Do this programmatically rather than relying on visual inspection, since redundant rows are easy to miss once the sheet has 30+ entries. Example:

```python
def dedupe_rows(rows):
    """rows: list of dicts with at least rule_text, scenario_type, expected_result keys.
    Keeps the first row for each unique (rule, scenario type, expected outcome) combination."""
    seen = set()
    deduped = []
    skipped = []
    for row in rows:
        key = (
            " ".join(row["rule_text"].split()).strip().lower(),
            row["scenario_type"].strip().lower(),
            " ".join(row["expected_result"].split()).strip().lower(),
        )
        if key in seen:
            skipped.append(row)
            continue
        seen.add(key)
        deduped.append(row)
    return deduped, skipped
```

  Report to the user how many rows were skipped as redundant and why, so nothing is silently dropped.
- Save to `/mnt/user-data/outputs/<TICKET>_Test_Cases.xlsx`.
- Present the file with `present_files` and briefly summarize how many rows were generated per sheet, which scenario types were covered (and skipped, if any), and how many redundant rows were removed.

## Step 5: Confirm before finalizing

Before presenting the file, do a final self-check:
1. Does every row's Part Number Rules column exactly match what the user described (no invented rule text)?
2. Does every row's Test Data / Part Number value trace back to the input sheet (no fabricated values)?
3. Does every row's Expected Result logically follow from the rule + Test Data?
4. Does the row set cover every scenario type from the ticket/test scenarios list, with no rule or scenario silently skipped?
5. Did the dedup pass remove all rows with identical (rule, scenario type, expected result) combinations?
6. Are there any scenario types you weren't able to cover confidently? If so, flag them to the user explicitly rather than silently omitting or guessing.

If at any point the ticket description is too thin to produce correct test cases (e.g. only a ticket number with no rule details), don't generate a speculative file — ask the user for the missing rule/behavior details first.
