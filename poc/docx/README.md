# POC DOCX Track Changes

Creates real insertion/deletion revisions from explicitly selected synthetic JSON proposals. No model calls, application architecture changes, real customer data, or production deployment.

```sh
python -m pip install -r poc/docx/requirements.txt
python -m unittest discover -s tests -v
python -m poc.docx.run .local-evidence/POC-DOCX-20261103-01
python -m poc.docx.track_changes input.docx changes.json tracked.docx
```

`run` writes synthetic input, selected proposals, tracked output, logs, hashes and result.json. `auto_status=PASS` never implies POC acceptance: Word UI gates remain BLOCKED/NOT_RUN. See TASKS.md for acceptance and manual steps. XML accept/reject projections only test the serialized semantics; they are not Microsoft Word actions.

Supported: exact replacement/deletion within one plain text run, including table cells; selected proposals only; preserved run formatting, surrounding text, unmodified package parts. Reject: existing document revisions, protected documents, content-control/field target paragraphs, overlapping targets, stale offsets/text, malformed XML/package and unsupported run nodes. No generic R1 export, paragraph insertion, cross-run replacement, clean-copy export or support claims for complex Word elements.

Package size limits are deliberately narrow POC resource bounds (10 MB compressed / 30 MB expanded), not changes to SRS upload limits. Source remains unchanged. This is not a malware scanner, signature verifier or production upload security boundary.

The repository is public: only synthetic generators, tests and non-sensitive metadata belong here. Store binary test outputs and screenshots in the test-run Drive folder. Do not upload the baseline or real documents to this public repository without separate authorization.
