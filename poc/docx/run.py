"""Run real synthetic DOCX export and tests; Word gate stays BLOCKED."""
import hashlib
import io
import json
import platform
import subprocess
import sys
import unittest
from datetime import datetime,timezone
from pathlib import Path
from poc.docx.fixture import fixture
from poc.docx.track_changes import patch_file

def main():
    out=Path(sys.argv[1] if len(sys.argv)>1 else '.local-evidence/POC-DOCX-20261103-01')
    out.mkdir(parents=True,exist_ok=True)
    data,changes=fixture();(out/'input.docx').write_bytes(data)
    (out/'changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf8')
    report=patch_file(out/'input.docx',out/'tracked.docx',changes)
    log=io.StringIO();suite=unittest.defaultTestLoader.discover('tests')
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    (out/'tests.log').write_text(log.getvalue(),encoding='utf8')
    report.update(test_run_id=out.name, tester='Codex automated runner', run_at=datetime.now(timezone.utc).isoformat(),
                  python=platform.python_version(),build_id=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                  working_tree_dirty=bool(subprocess.check_output(['git','status','--porcelain'],text=True).strip()),
                  auto_status='PASS' if result.wasSuccessful() and result.testsRun else 'FAIL',
                  test_count=result.testsRun, failures=len(result.failures),errors=len(result.errors),
                  poc_status='BLOCKED',word_gate='BLOCKED: Microsoft Word UI unavailable',
                  manual_cases={f'MANUAL-WORD-{i:02}':'NOT_RUN' for i in range(1,5)},drive_evidence_uri=None,
                  limits='Single-run replacements; no general paragraph/cross-run editing. XML projection is not Word acceptance.')
    (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='SHA256SUMS.json'}
    (out/'SHA256SUMS.json').write_text(json.dumps(hashes,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if result.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
