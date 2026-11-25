# Evaluation

Development-only checks for the screenplay Skill. These files are not copied into the installed Skill or GPT knowledge package.

## Deterministic Checks

```powershell
python .\eval\run_static_checks.py
python .\eval\make_mutants.py
```

`run_static_checks.py` verifies UTF-8/NFC, Markdown fences, owner routing, the
canonical 14-field schema, ambiguous conditional wording, deployable-file
contamination, GPT file counts/length health, and contract-schema integrity.

`validate_delivery.py` also requires one canonical `timing_mode` and one
`active_modules` declaration in new output. These declarations must equal the
contract-selected modes on both LF and CRLF systems; historical inputs receive
compatibility warnings instead.

`make_mutants.py` requires zero false positives on valid fixtures and catches
eleven isolated hard defects:

- dialogue punctuation drift
- CUT gap/renumbering
- missing CUT field
- missing scene director-map field
- stale event residue
- deprecated asset path
- duplicate scene master
- illegal early literal POV
- GEN timing overage by `0.1`
- document/contract timing-mode mismatch
- rights source/use notice placed before another delivery section

It also confirms that structurally synchronized but bookish dialogue receives a semantic-review warning rather than a false static verdict.

## Forward Matrix

Fresh writers should receive only a raw brief and the current Skill/GPT files. Keep private source drafts and generated candidates under ignored `eval/.artifacts/`; do not commit regression stories, diagnoses, asset paths, or expected answers.

```powershell
python .\eval\run_forward_matrix.py `
  --manifest .\eval\.artifacts\forward\matrix.json `
  --json-out .\eval\.artifacts\forward\report.json
```

Use at least:

- an unseen canon revision without access to the accepted answer
- a different genre with a hard total and shorter GEN limit
- a soft runtime phrase that must remain `silent-default`
- a named third-party recreation that defaults to `rights-asserted`, preserves
  full authorized asset/lyric slots, and places its source/use notice last

Static passing is not enough. Run two blind semantic reviews: actor/dialogue and edit/video-generation. Both reviewers see only the raw brief and candidate, and may veto event naturalness, spoken dialogue, performance, viewpoint legality, transition causality, or independent GEN usability.
