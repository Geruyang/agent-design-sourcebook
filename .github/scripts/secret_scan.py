"""Run pinned Gitleaks; publish metadata only, never secret/match/line contents."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--repo', required=True)
    a.add_argument('--scanner', required=True)
    a.add_argument('--base')
    a.add_argument('--head', default='HEAD')
    a.add_argument('--audit', action='store_true')
    a.add_argument('--staged', action='store_true', help='Scan staged additions before local publication')
    a.add_argument('--output', required=True)
    a = a.parse_args()
    policy = Path(__file__).resolve().parent.parent / 'security'
    env = dict(os.environ)
    for key in list(env):
        if key.startswith('GITLEAKS_'):
            env.pop(key)
    head = subprocess.check_output(['git', '-C', a.repo, 'rev-parse', '--verify', a.head + '^{commit}'], env=env).decode().strip()
    if not re.fullmatch('[a-f0-9]{40,64}', head):
        raise ValueError('invalid head')
    if a.audit and a.staged:
        raise ValueError('--audit and --staged are mutually exclusive')
    if a.staged:
        scope = 'staged additions'
    elif a.audit:
        scope = '--all --diff-merges=separate'
    else:
        if not a.base or not re.fullmatch('[a-f0-9]{40,64}', a.base):
            raise ValueError('explicit full base commit SHA required; zero/new branch needs audit')
        base = subprocess.check_output(['git', '-C', a.repo, 'rev-parse', '--verify', a.base + '^{commit}'], env=env).decode().strip()
        scope = base + '..' + head + ' --diff-merges=separate'
    with tempfile.TemporaryDirectory(prefix='secret-scan-') as temp:
        raw = Path(temp) / 'redacted.json'
        cmd = [a.scanner, 'git', a.repo, '--log-opts', scope, '--config', str(policy / 'gitleaks.toml'), '--gitleaks-ignore-path', str(policy / 'empty.gitleaksignore'), '--ignore-gitleaks-allow', '--redact=100', '--no-banner', '--no-color', '--report-format=json', '--report-path', str(raw)]
        if a.staged:
            cmd = cmd[:3] + ['--pre-commit', '--staged'] + cmd[5:]
        completed = subprocess.run(cmd, capture_output=True, env=env)
        findings = json.loads(raw.read_text(encoding='utf-8')) if raw.exists() else None
        if completed.returncode not in (0, 1) or findings is None:
            # Never expose arbitrary stderr. Tool error is distinct from findings.
            result = {'status': 'scanner_error', 'exit_code': completed.returncode, 'scope': scope, 'stderr_sha256': hashlib.sha256(completed.stderr).hexdigest()}
            code = 2
        else:
            safe = [{k: row.get(k) for k in ['RuleID', 'File', 'StartLine', 'EndLine', 'Commit', 'Fingerprint']} for row in findings]
            risk_path = 'code/anomalyco/opencode/packages/http-recorder/test/redaction.test.ts'
            risk = {'alert': 8, 'path': risk_path, 'validity': 'unknown; no credential usage', 'not_allowlisted': True} if (Path(a.repo) / risk_path).exists() else None
            status = 'findings' if safe else ('unresolved_manual_risk' if a.audit and risk else 'clean_in_scanned_scope')
            result = {'status': status, 'scope': scope, 'audit': a.audit, 'count': len(safe), 'findings': safe, 'known_unresolved_risk': risk, 'baseline_clean_claimed': bool(a.audit and not safe and not risk)}
            code = 1 if safe or (a.audit and risk) else 0
        output = Path(a.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'status': result['status'], 'count': result.get('count'), 'report': str(output)}))
        return code


if __name__ == '__main__':
    raise SystemExit(main())
