# Result comparison map

The default domain-enabled reviewer now builds a deterministic map before inference. The same map and source tools are available to the single reviewer and PRA. No extra model call is added.

The map links explicit figure and table references to their extracted captions and tables. Each node records its manuscript block, content hash, page when known, literal model labels, numeric spans, and source text. Links are references, not assertions that two analyses are equivalent. Missing or duplicate targets remain visible as extraction limitations.

The bounded overview prioritizes linked displays with different model labels. This can reveal a caption calling a linked multiple-regression table an SLR model, but it cannot decide whether the difference is a reporting error. The investigator must inspect outcome, population or denominator, model, timepoint, units, scale, and effect label before comparing numbers.

Two tools support this work:

- `inspect_results` returns a bounded neighborhood around a manuscript block, or an overview when the block ID is empty.
- `record_comparison` records two exact textual quantities with their comparison dimensions. Unknown context produces an incomplete result. Different model, population, scale, metric, units, or timepoint produces a different-context result. Equal context with different numbers produces a reconciliation question, not a verified defect.

Text quotations and complete numeric tokens are validated. Context labels are investigator assessments. Image-only values are not transcribed or verified automatically. Use the existing figure-page tool to inspect them, and preserve uncertainty if access is unavailable. The arithmetic tool remains available for simple calculations. No underlying analysis or large dataset is rerun.

The map and comparison records are saved in review artifacts, shown in the interface, and retained in exported revision packages. Comparison tool calls consume the same existing per-condition allowance. They do not create a separate budget.

## Offline use

```text
python3 -m paper_workspace result-map MANUSCRIPT_WORKSPACE --output result-map.json
```

The ecology paper from the previous panel is a development fixture. Its map links the Figure 3 caption in `b0037` to the multiple-regression table in `b0039` and flags differing model labels for inspection. It does not extract the plotted slope or R squared from the image. This is an infrastructure check on a previously inspected paper, not fresh evidence of improved review accuracy.

Current limits include literal numbered references, incomplete support for grouped display ranges, no automatic image transcription, and no semantic claim extraction. Long source text is shortened only in the tool overview with an explicit truncation flag. The complete source and full map remain available.
