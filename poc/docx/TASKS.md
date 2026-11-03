# POC DOCX task contracts

Baseline: AI Law SRS 1.1.15, J.7; POC/POC_PROTOCOL.md. No architecture change.
Only synthetic data. Owner acceptance required; no merge or production deployment.

| Task | Acceptance | Test cases |
|---|---|---|
| DOCX-01 | Synthetic fixture with Unicode, heading, numbering, header/footer, table and five proposals | fixture open; original SHA unchanged |
| DOCX-02 | Explicitly selected, exact single-run text replacements emit real w:ins/w:del and preserve other ZIP parts | selected only; old/new views; unique revision IDs; metadata; whitespace; formatting |
| DOCX-03 | Invalid request/package fails without writing output | missing/duplicate ID; stale text; locked SDT; field; malformed XML; existing revisions; invalid offsets; unsafe ZIP |
| DOCX-04 | Word opens without repair; accept two/reject one; save/reopen preserves header/table/numbering | MANUAL-WORD-01 through 04; screenshots, hashes, reviewer, run ID required |
| DOCX-05 | CI on PR runs the same automatic tests; evidence kept by run | Actions log; Drive folder if available |

POC limit: replacements within one plain text run in a body/table paragraph. No cross-run or paragraph insertion implementation. Existing revisions, field-containing target paragraphs and all content-control target paragraphs are rejected. Complex elements elsewhere are preserved bytewise at package-part level and reported as warnings. This is NOT full J.7 compatibility or a production import security boundary.

Manual Word cases (NOT_RUN until real Word evidence exists):
1. Open tracked.docx, Review All Markup; no repair dialog; only selected changes visible.
2. Accept first two replacement pairs, reject third; verify expected text and unchanged original.
3. Save, close, reopen; inspect header/footer, numbering, table and text; record output hash.
4. Capture before/after screenshots to the test-run Drive folder and record Word version/reviewer.
