"""Run pinned Gitleaks; publish metadata only, never secret/match/line contents."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request


def pinned_rules(policy, temp):
    """Keep upstream rule fixtures out of Git, with identical pinned rules."""
    legacy = policy / 'gitleaks.toml'
    if legacy.exists():
        if hashlib.sha256(legacy.read_bytes()).hexdigest() != '9f581d81a887e17bbccfe05d0899ea34b4bf66633fe9eec6f8c58732a51507b5':
            raise ValueError('legacy rules checksum mismatch')
        return legacy
    data = urllib.request.urlopen('https://raw.githubusercontent.com/gitleaks/gitleaks/v8.28.0/config/gitleaks.toml', timeout=60).read()
    if hashlib.sha256(data).hexdigest() != 'c3bee40d87bb4689e3f5ffa5cc0315f7e6e4d43f4e9388397fca59f29407b432':
        raise ValueError('official pinned rules checksum mismatch')
    lines = data.splitlines(keepends=True)
    # Exact edits in this checksum-pinned version: remove the four broad path allowlists.
    for start, end, replacement in [(2138,2143,[]), (2113,2118,[]), (2094,2097,[b'paths = [] # no path-wide exclusions\n']), (18,45,[b'paths = [] # no path-wide exclusions\n'])]:
        lines[start:end] = replacement
    output = b''.join(lines)
    if hashlib.sha256(output).hexdigest() != '9f581d81a887e17bbccfe05d0899ea34b4bf66633fe9eec6f8c58732a51507b5':
        raise ValueError('reviewed rules checksum mismatch')
    destination = Path(temp) / 'gitleaks.toml'
    destination.write_bytes(output)
    return destination


def reviewed_findings(repo, findings, policy, env):
    """Recognize individually reviewed immutable findings, never whole paths."""
    source = policy / 'reviewed-baseline.json'
    records = json.loads(source.read_text(encoding='utf-8')).get('findings', []) if source.exists() else []
    accepted = {'documentation_placeholder', 'synthetic_test_fixture', 'non_secret_code_or_identifier'}
    by_fingerprint = {}
    for record in records:
        if 'CommitParts' in record:
            parts = record['CommitParts']
            if not isinstance(parts, list) or len(parts) != 2 or not all(isinstance(part, str) and re.fullmatch('[a-f0-9]{20}', part) for part in parts):
                raise ValueError('invalid split commit identifier')
            record = {**record, 'Commit': ''.join(parts)}
        fingerprint = record['Fingerprint']
        if fingerprint in by_fingerprint or record.get('disposition') not in accepted:
            raise ValueError('invalid or duplicate reviewed finding')
        if not record.get('evidence') or not re.fullmatch('[a-f0-9]{64}', record.get('blob_sha256', '')):
            raise ValueError('review requires evidence and immutable blob digest')
        by_fingerprint[fingerprint] = record
    pending, reviewed, cache = [], [], {}
    fields = ['RuleID', 'File', 'StartLine', 'EndLine', 'Commit', 'Fingerprint']
    for finding in findings:
        safe = {key: finding.get(key) for key in fields}
        record = by_fingerprint.get(safe['Fingerprint'])
        if record and all(record.get(key) == safe[key] for key in fields):
            commit, file = safe['Commit'], safe['File']
            if not re.fullmatch('[a-f0-9]{40,64}', commit) or '\x00' in file:
                raise ValueError('invalid reviewed object locator')
            locator = commit + ':' + file
            if locator not in cache:
                blob = subprocess.check_output(['git', '-C', repo, 'show', locator], env=env)
                cache[locator] = hashlib.sha256(blob).hexdigest()
            if cache[locator] == record['blob_sha256']:
                reviewed.append({**safe, 'disposition': record['disposition'], 'evidence': record['evidence']})
                continue
        pending.append(safe)
    return pending, reviewed


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
        rules = pinned_rules(policy, temp)
        cmd = [a.scanner, 'git', a.repo, '--log-opts', scope, '--config', str(rules), '--gitleaks-ignore-path', str(policy / 'empty.gitleaksignore'), '--ignore-gitleaks-allow', '--redact=100', '--no-banner', '--no-color', '--report-format=json', '--report-path', str(raw)]
        if a.staged:
            cmd = cmd[:3] + ['--pre-commit', '--staged'] + cmd[5:]
        completed = subprocess.run(cmd, capture_output=True, env=env)
        findings = json.loads(raw.read_text(encoding='utf-8')) if raw.exists() else None
        if completed.returncode not in (0, 1) or findings is None:
            # Never expose arbitrary stderr. Tool error is distinct from findings.
            result = {'status': 'scanner_error', 'exit_code': completed.returncode, 'scope': scope, 'stderr_sha256': hashlib.sha256(completed.stderr).hexdigest()}
            code = 2
        else:
            safe, reviewed = reviewed_findings(a.repo, findings, policy, env)
            risk_path = 'code/anomalyco/opencode/packages/http-recorder/test/redaction.test.ts'
            risk = {'alert': 8, 'path': risk_path, 'validity': 'unknown; no credential usage', 'not_allowlisted': True} if (Path(a.repo) / risk_path).exists() else None
            if any(row['File'] == risk_path and row['RuleID'] == 'gcp-api-key' and row['StartLine'] == 80 and row['Commit'] == 'e64638152e52154826ef0a5a014c5ba9fc20e31e' for row in reviewed):
                risk = None
            status = 'findings' if safe else ('unresolved_manual_risk' if a.audit and risk else ('reviewed_baseline_only' if reviewed else 'clean_in_scanned_scope'))
            result = {'status': status, 'scope': scope, 'audit': a.audit, 'count': len(safe), 'findings': safe, 'scanner_count': len(findings), 'reviewed_count': len(reviewed), 'reviewed_findings': reviewed, 'known_unresolved_risk': risk, 'baseline_clean_claimed': bool(a.audit and not safe and not risk and not reviewed)}
            code = 1 if safe or (a.audit and risk) else 0
        output = Path(a.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'status': result['status'], 'count': result.get('count'), 'report': str(output)}))
        return code


if __name__ == '__main__':
    raise SystemExit(main())
