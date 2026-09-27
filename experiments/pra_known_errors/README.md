# Paired known-error development experiment

This experiment tests an investigation team against a six-stage sequential reviewer using Sol at medium reasoning effort. Both receive the same complete manuscript, shared claim map, manuscript tools, stage allowances, and final review limits. The team investigates three work orders independently, then exchanges a defense and reply before adjudication. The sequential reviewer carries all explicit notes through the same six stages.

Two original and altered paper pairs come from the previously selected FLAWS sample. Review generation sees opaque input IDs and no annotations. Evaluation follows generation and uses two anonymous judgments with reversed candidate order. The primary screen requires more detected altered-paper targets with no additional corresponding allegation on either original and no additional jointly contradicted major concern on any input. All four inputs must finish. Supported detections are reported separately. A positive screen remains a development result pending manual audit.

Full findings and dispositions are preserved. Primary reports contain at most five concerns and 900 words. Actual token use is reported because matching stages does not match realized compute. Public benchmark contamination, annotation ambiguity, same-model judging, and fresh-session memory are limitations.

Run offline tests with the project Python using `-m unittest discover -s experiments/pra_known_errors -v`. Run `study.py prepare` to freeze code, protocol, inputs, and evaluation labels. Run `study.py run` only after verifying subscription authentication and recording zero paid credits. A STOP file prevents new calls. Never edit a frozen runner. Start a new version for any change.
