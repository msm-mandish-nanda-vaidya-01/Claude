# Test Case Standards

**Status:** Mandatory  
**Audience:** All engineers — QA  
**Author:** Suzal Shrestha

---

## Table of Contents

1. [Why We Maintain Test Cases](#1-why-we-maintain-test-cases)
2. [Test Case Format](#2-test-case-format)
3. [Required Fields](#3-required-fields)
4. [Writing Good Test Cases](#4-writing-good-test-cases)
5. [Coverage Areas](#5-coverage-areas)
6. [Linking Test Cases to Jira](#6-linking-test-cases-to-jira)
7. [Marking Pass and Fail](#7-marking-pass-and-fail)

---

## 1. Why We Maintain Test Cases

Test cases are the QA team's primary artifact. They serve three purposes:

1. **Consistency** — every QA run covers the same scenarios, regardless of who is running it
2. **Traceability** — each test case links to a feature or Jira ticket, so coverage gaps are visible
3. **Regression safety** — when a fix is deployed, the relevant test case is re-run to confirm the fix and to catch any regressions

Without maintained test cases, testing becomes ad hoc — coverage varies by person, issues get missed, and there is no record of what was tested before a release.

**Minimum expectation:** Every new feature or bug fix that goes to DEV must have at least one test case written or updated before QA sign-off.

---

## 2. Test Case Format

Test cases are maintained in a shared **Excel file**. Each test case is one row. The columns are fixed — do not add, remove, or reorder columns without discussing with the QA lead first.

The columns in order are:

| # | Column | Description |
|---|---|---|
| 1 | **SN** | Serial number — sequential integer, unique within the sheet |
| 2 | **Date** | Date the test was run (`DD/MM/YYYY`) |
| 3 | **URL** | The exact URL of the page or API being tested |
| 4 | **Example Part Number** | The specific part number used in this test run |
| 5 | **Test Case Description** | One sentence describing what is being tested |
| 6 | **Precondition** | What must be true before the test can run |
| 7 | **Test Steps** | Numbered steps (1. Step one 2. Step two ...) |
| 8 | **Expected Result** | Exactly what should happen |
| 9 | **Actual Result** | What actually happened — fill in after running |
| 10 | **Screenshots** | Attach a screenshot of the result (mandatory for failures) |
| 11 | **OK/NG** | `OK` if the actual result matches expected, `NG` if it does not |

Each test case is one row in the Excel sheet. The columns are defined above.

### Sheet organisation

The Excel file is organised by test area. Each area has its own sheet tab:

| Sheet | What it covers |
|---|---|
| `Website` | Frontend part number search, replacement display, page load |
| `Dashboard` | Pipeline trigger, status display, run history, S3 Explorer |
| `GDB Pipeline` | GDB registration — happy path, error cases, file format cases |
| `XDB Pipeline` | XDB migration — indexing, OpenSearch, S3 Vector |
| `API` | `default_replacements`, `custom_replacements`, `part-number` endpoints |
| `Validation Tool` | File validation — valid files, invalid files, edge cases |
| `Regression` | Cross-cutting regression scenarios run after any significant change |

---

## 3. Required Fields

Every test case row must have all columns filled before it is considered complete. Fields left blank are treated as not run.

| Field | Rules | Example |
|---|---|---|
| **SN** | Sequential integer, never repeated within the same sheet | `1`, `2`, `3` |
| **Date** | The date you ran the test — fill in on the day you run it | `01/04/2026` |
| **URL** | The exact URL under test — do not abbreviate | `https://stg01.cross-dev.misumi-ec.com` |
| **Example Part Number** | The specific part number you entered or used in this test | `KED4-10`, `JIRA-1363-01` |
| **Test Case Description** | One sentence — what behaviour is being verified | `Backend should send part_number_local for all replacement results` |
| **Precondition** | State the system must be in before this test runs | `Search part number with replacement data registered in XDB` |
| **Test Steps** | Numbered steps — write them so anyone can follow without asking questions | `1. Search part number  2. Check API response of default_replacements  3. Verify part_number_local is present` |
| **Expected Result** | Exactly what should happen — specific, not vague | `part_number_local field is present and populated for all replacement results` |
| **Actual Result** | Exactly what happened — fill in after running the test | `part_number_local is being sent correctly` |
| **Screenshots** | Screenshot of the result — mandatory for NG, recommended for OK | Attach inline or paste into the cell |
| **OK/NG** | `OK` — actual matches expected. `NG` — actual does not match, raise a Jira bug | `OK` |

---

## 4. Writing Good Test Cases

### Title

The title must be a complete sentence that describes **what scenario is being tested** and **what the expected outcome is**.

| Good | Bad |
|---|---|
| `GDB pipeline completes successfully for a valid Input file with KOR subsidiary code` | `GDB pipeline test` |
| `Validation Tool rejects Input file with missing part_number column` | `Validation test 3` |
| `Website returns no results message (not an error) when part number is not registered` | `Search edge case` |

### Preconditions

Preconditions are the state the system must be in before the test starts. Be specific.

| Good | Bad |
|---|---|
| `Test data for ticket NDFDPAPJ-1363 uploaded to DEV S3 and GDB pipeline completed with Success status` | `System is ready` |
| `User is on the DEV website homepage (https://stg01.cross-dev.misumi-ec.com)` | `Browser is open` |

### Steps

Steps must be specific enough that any QA team member can run the test without asking questions.

- Use numbered steps
- Specify the exact URL if navigating to a page
- Specify the exact input values (part numbers, file names, search terms)
- Specify which button or action to take

### Expected result

The expected result must be a single, verifiable outcome. If you need to check multiple things, split the test case.

| Good | Bad |
|---|---|
| `HTTP 200 response with non-empty results array returned by /default_replacements` | `API works correctly` |
| `Pipeline status changes to "Failed" and error is visible in CloudWatch with error_code DATA_001` | `Pipeline shows an error` |

---

## 5. Coverage Areas

Every test case belongs to one of these coverage areas. When writing test cases, make sure all areas are covered for any feature or change being tested.

### Happy path

The normal, expected flow with valid inputs. This is the minimum — every feature must have at least one happy path test case.

### Error cases

What happens when something goes wrong — invalid input, missing data, service unavailable. Confirm the system fails gracefully with an appropriate message rather than crashing.

### Edge cases

Boundary conditions — empty search, maximum number of parts, a part that exists in GDB but not XDB, a file with the minimum required columns only.

### Regression

After a fix or change, re-run the test cases for adjacent functionality to confirm nothing was broken. See [BUG_TESTING_PROCESS.md](./BUG_TESTING_PROCESS.md) — Section 5 for guidance on what to regression test.

---

## 6. Linking Test Cases to Jira

Every test case must have a Jira ticket reference in the **Jira Ticket** field.

- For new features: link to the feature ticket (e.g. `NDFDPAPJ-1636`)
- For bug fixes: link to the bug ticket (e.g. `NDFDPAPJ-1700`)
- For regression test cases that cover multiple tickets: link to the primary ticket or use `REGRESSION`

When a bug is raised during testing, add the bug ticket number to the **Notes** field of the test case that exposed it.

---

## 7. Marking OK and NG

### OK/NG values

| Value | When to use |
|---|---|
| `OK` | The actual result matches the expected result exactly |
| `NG` | The actual result does not match the expected result — raise a Jira bug ticket immediately |

> If the test cannot be run (pipeline is down, environment unavailable), leave the row incomplete and add a note in the Actual Result column explaining what is blocking.

### Rules

- **Never mark OK if you skipped a step** — run all steps in order
- **Always fill in Actual Result** — even for OK, record what you observed
- **Screenshot is mandatory for every NG** — without a screenshot, the developer cannot start debugging
- **Raise a Jira bug the same day you mark NG** — do not batch bug reports at the end of a test cycle

### After a bug is fixed

When a developer fixes a bug and deploys to DEV:

1. Re-run the test case using the original steps
2. Update the Date to the re-test date
3. Fill in the new Actual Result
4. Update OK/NG to `OK` if the fix is verified
5. Move the Jira bug ticket to `Done` only after you mark it OK
