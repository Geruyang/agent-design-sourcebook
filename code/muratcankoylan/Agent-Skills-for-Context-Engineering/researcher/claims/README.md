# Claim Provenance

Claim provenance records volatile, numeric, benchmark, or externally sourced claims that appear in published skills. The goal is not to cite every sentence. It is to make claims that can rot easy to audit and revalidate.

Each line in `index.jsonl` records:

- `claim_id`: stable identifier
- `claim_text`: concise statement of the claim
- `owning_skill`: skill that uses the claim
- `section`: section where the claim appears
- `source_url`: upstream source
- `retrieved_at`: date or run artifact that captured the source
- `evidence_strength`: `primary`, `secondary`, `anecdotal`, or `derived`
- `volatility`: `low`, `medium`, or `high`
- `last_reviewed`: date or run ID for the latest review

High-volatility claims should be reviewed before release-sensitive updates and after major model or provider changes.
