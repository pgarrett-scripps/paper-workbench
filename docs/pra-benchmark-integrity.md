# Benchmark integrity finding and next test

The claim-investigation prototype exposed a reference applicability problem before
its first comparison was scored. The supplied TableQA manuscript already contains
information requested by several human reference concerns. This should have been
resolved before interpreting the earlier coverage scores as evidence about review
quality.

## Directly verified evidence

The evidence was checked against the frozen local manuscript, not just model output.
Exact source chunks and reference records are preserved in
`runs/pra-version-audit-v1/local_evidence.json`.

| Reference | What the reference asks for | Information in the supplied manuscript |
| --- | --- | --- |
| R2 | Testing beyond GPT, including open models | E0138 and E0139 report base and TIDE results for Llama 2, Llama 3, GLM 4, Gemini 1.5, and Claude 3.5 |
| R3 | Response time and token consumption | E0152 to E0154 introduce a time and token appendix and a table of operation times and token expressions |
| R13 | Verification failure frequency and maximum iterations | E0146 and E0147 describe first-iteration completion, fewer than two percent unresolved after four iterations, and an error default |

These observations answer parts of the reference requests. They do not prove that
all related concerns are resolved. Cross-model protocols may still be unclear,
end-to-end cost accounting may be incomplete, and retry state transitions may still
be underspecified. A correct review must distinguish those remaining problems
from saying the reported information is entirely absent.

The old manifest explicitly marks manuscript-review pairing and figure access as
unverified. The mirrored source contains the published manuscript text without
historical review timestamps or manuscript revision hashes. A later manuscript
version is a plausible explanation, but exact chronology has not been established.
Human reviewers can also overlook information that was already present.

OpenReview's public forum and API returned a browser verification challenge during
the audit. The API responses and requested URLs are saved in
`runs/pra-version-audit-v1/UwcZEoNP19`. No challenge was bypassed and no private
credentials were accessed. Official [OpenReview edit documentation](https://docs.openreview.net/getting-started/objects-in-openreview/introduction-to-edits)
describes the revision records needed to establish the chronology.

## Consequences for interpretation

The previous numerical scores remain unchanged and reproducible under their saved
scoring procedures. This finding does not reverse the rankings or show that PRA
outperforms a single agent. It does mean that concern overlap against these
unverified references is not an adequate target for architecture optimization or
a claim about scientific review quality.

Do not silently remove inconvenient references, adjust denominators, or rescore only
favorable examples. An applicability audit or corrected version pairing must be
reported as a new evaluation with a separate frozen corpus and analysis.

## Preserved prototype and bounded continuation

The prototype is in `experiments/pra_claim_investigation`. Its five offline tests
passed. It implements method reconstruction, concrete work orders, manuscript
reading and search, bounded executable numerical and logical checks, defender
responses, investigator replies, and adjudication of a complete concern ledger.
The main comparator performs the same six stages sequentially with full explicit
notes. Both use Sol medium, the same tools, and the same final review limits.

The first run was stopped at the initial investigation boundary. All four active
calls saved successfully. There were no failed calls, retries, unknown usage, or
scoring calls. The frozen code and inputs are preserved. The investigations include
operational reconstructions and 13 calculation receipts. These are research
artifacts, not yet verified scientific discoveries or evidence of superiority.

Continue with a small existing known-error benchmark while independently seeking
verified manuscript-review pairs. [FLAWS](https://arxiv.org/abs/2511.21843) supplies
documented claim-invalidating edits and corresponding error-location records.
Its [public release](https://huggingface.co/datasets/xasayi/FLAWS) includes altered
paper sources and error annotations. Its general-CS extension is small enough
to inspect selectively without downloading the full 11.6 GB release.

Select a reproducible small sample before seeing system outputs. Keep inserted
error descriptions and locations outside generation inputs. Verify the edit is
present in the staged manuscript and keep paired original inputs when available.
Treat the originals as controls for the inserted allegation, not as papers known
to contain no errors. Use the same input evidence, tools, and output budget for
the team and a strong single workflow. Preserve failures and blind scoring.

This tests detection of documented inserted flaws. It is a separate endpoint from
recovering human review concerns and does not alone validate complete peer review.
Published benchmark annotations are also fallible and may be in model training
data. Audit a small number of detected and missed cases before a superiority claim.

Approximately four million observed tokens remain from the current five-million
token development allowance. New runs require their own frozen manifests, efficient
schema references, and practical budget calibration. All previous runs remain
stopped. No paid credits, resets, API-key billing, or Astra calls are authorized.
