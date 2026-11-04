"""Expose SARIF locations/rules only; never print messages, snippets or secret values."""

import json
import sys
from pathlib import Path


def escaped(value: object) -> str:
    return str(value).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')


report = Path(sys.argv[1] if len(sys.argv) > 1 else 'results.sarif')
if report.is_file():
    findings = [result for run in json.loads(report.read_text())['runs'] for result in run.get('results', [])]
    print(f'Secret scan: {len(findings)} candidate(s); values omitted; complete redacted SARIF is an artifact.')
    for result in findings[:40]:
        location = (result.get('locations') or [{}])[0].get('physicalLocation', {})
        path = location.get('artifactLocation', {}).get('uri', 'unknown')
        line = location.get('region', {}).get('startLine', '?')
        rule = result.get('ruleId', 'unknown-rule')
        print(f'::warning::{escaped(rule)} at {escaped(path)}:{escaped(line)} (value omitted)')
else:
    print('Secret scanner did not produce a SARIF report; inspect the scanner step status.')
