# Secret scanning scope

Incremental gate scans introduced commits/staged additions, not legacy baseline cleanliness. Separate full-history audit intentionally fails on unreviewed findings. Pattern matches do not prove credential validity. Sourcebook alert #8 was subsequently confirmed by the repository owner as constructed test data; its exact historical fixture record carries that human-confirmation evidence, without claiming provider validity; reviewed-evidence entries are documentation only, not suppressions. No repository-wide source/test/vendor path exclusions. Official scanner and assets are pinned in tool-lock.json. PR policy is taken from base commit; initial bootstrap PR reads policy blobs only from pinned, previously validated commit SHAs; never arbitrary PR HEAD. No application code, credentials or account business is executed by scans. Reports publish metadata only.

Both incremental and full-history scans include --diff-merges=separate, including conflict-resolution-only merge changes. PR target is GitHub-generated merge SHA, while policy remains trusted base/reviewed bootstrap. Per-parent merge patches may duplicate pattern counts; counts are not unique credentials.

Reviewed historical findings are recorded individually in `reviewed-baseline.json`.
An entry is recognized only when its fingerprint, rule, file, line range, commit,
and SHA-256 of that immutable Git blob all match. Each entry states the inspected
non-secret evidence and its classification. A new commit, changed value/context,
or unmatched finding requires a fresh review and fails the gate. Reports retain
the scanner total, reviewed findings, and unresolved findings separately; a
reviewed baseline is never described as having no scanner findings. No directory,
test filename, token pattern, or future occurrence is automatically exempted.

Git commit IDs in the review table are stored as two explicit 20-hex halves
(`CommitParts`), then validated and reconstructed before comparison. This avoids
an upstream legacy-token rule matching bare Git IDs; it does not exempt the
review table from scanning.

The official rule file is downloaded to a temporary directory at scan time.
Both its original checksum and the checksum after removing the same four broad
path allowlists are enforced. The effective rules remain byte-for-byte identical
to the previous reviewed policy. Known-public sample literals embedded in that
upstream rule file are no longer copied into the tracked repository.

The exact Casdoor initialization signing key in the historical snapshot is a real, public reference key. The owner confirms these sources were collected only and never deployed here. It is recorded under a separate bounded disposition with an audit warning, not called a false positive, revoked key, or safe production key. New commits/keys still fail pending review.

The owner explicitly chose to retain collected source and accept the exact unresolved initial-reference risks. cknowledged-reference-risks.json records only those immutable initial-commit fingerprints and blob digests. Full audits preserve these unresolved findings in count/findings and emit visible warnings; blocking_count excludes only these exact acknowledged historical records. They are not labelled false positives, inactive, or revoked. Incremental scans do not apply this manifest; new commits, changed bytes or metadata, unmatched findings and scanner errors still fail.
