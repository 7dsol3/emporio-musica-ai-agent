# Validation record

## Automated checks

Observed locally on Windows x64, Python 3.12.10:

```text
python -m pytest
49 passed, 1 warning in 34.42s

python -m compileall -q emporio scripts
exit code 0
```

The warning is an upstream Starlette TestClient deprecation notice about its
HTTPX test transport; it is not an application failure. Exact exercised package
versions are in `requirements.lock`. The GitHub workflow additionally defines
Python 3.11/3.12 checks on Windows and Ubuntu; this local result does not claim
that a remote job has already run.

Coverage includes monetary validation and rounding, exact budget boundaries,
current snapshot reads, availability status, active/inactive promotion behavior,
PIX nonstacking, installment minima, exact BRL 500 shipping ambiguity, seven-day
return boundaries, PDF page references, customer data minimization, ownership
isolation, invalid verification, audit restart/tampering, session reset,
cross-origin/Host checks, request bounds, verification throttling, bilingual
output, holiday-aware scheduled opening, native function-call protocol, safe
provider fallback, missing receipt facts and conflicting model intent.

## Real local model evaluation

Server: official llama.cpp CPU build `b12024`.
Model: official Qwen3-0.6B GGUF, Q8_0, pinned revision and SHA-256 in
`PROVENANCE.md`. No paid API or remote inference was used.

`python scripts/capture_examples.py` captured five actual English conversations
and asserted their important outcomes. The final report is
[`live-evaluation.json`](live-evaluation.json).

| Observation | Result |
| --- | --- |
| Stateful scenarios | 5 |
| Customer turns | 13 |
| Accepted model-selected plans | 9 |
| Model attempts resolved through the explicit local fallback | 2 |
| Scope replies handled locally without model inference | 2 |
| Scenario assertions | PASS |
| Median model-attempt end-to-end latency | 7,660.7 ms |
| Model-attempt latency range | 7,232.3-8,563.0 ms |

These are thirteen scripted turns over one supplied dataset, not an estimate
of general language-model accuracy. The two fallbacks are visible in the
conversation receipts; they are not counted as successful neural plans.

The checked outcomes include a BRL 1,000 acoustic-guitar filter, resolving the
first result before an installment question, the 8% Taylor promotion without
an additional PIX discount, a four-calendar-day online-return example,
verification before order disclosure, cross-customer access refusal, both
address and hours, and an unrelated/injection request without tool access.

## Observed failures and corrections

1. **Substring product search:** short query tokens matched inside unrelated
   words. Token-level matching corrected the search; the original focused
   regression checks passed after the change.
2. **Unknown model substitution:** an unknown Takamine model fell back to a
   brand-only search. Model terms are retained so an absent model returns no
   match rather than silently substituting another product.
3. **English catalog terminology:** the real model called the correct tool
   with `acoustic guitar`, but the Portuguese descriptions did not contain that
   phrase. Shared tool normalization maps category terms before applying model/
   brand filters. The live budget query now returns the expected instruments.
4. **Stateful model repetition:** the small model repeated its prior catalog
   search instead of selecting the first result and then quoting installments.
   [`evidence/initial-followup.md`](evidence/initial-followup.md) preserves the
   observed replies and receipts. Explicit locally resolved product/payment
   intent now takes precedence when a model plan conflicts. A dedicated
   regression and the repeated live scenario passed, with two honest fallbacks.
5. **Unsupported/dropped policy topic:** the model originally produced a free
   text topic, `address and opening hours`, which was not a defined card.
   [`evidence/initial-policy-topic.md`](evidence/initial-policy-topic.md) preserves
   that response. Topic arguments are now enumerated, and the execution guard
   checks that explicit requested topics are retained. The repeated live
   conversation includes both the address and opening hours.

The initial aggregate receipts remain at
[`evidence/initial-live-evaluation.json`](evidence/initial-live-evaluation.json).
That initial capture was not a successful final evaluation.

## Browser and visual checks

`scripts/check_ui.py` exercises a fresh isolated Chromium/Chrome test profile.
It checks initial readiness, grounded chat, catalog/policy views, order
verification and tracking, session reset, mobile layout, and the Portuguese
interface and response. The machine's integrated-browser/native-control bridge
was unavailable; application checks use a dedicated headless test browser,
without connecting to a personal browser profile.

The observed report and actual screenshots are stored in
[`ui-check.json`](ui-check.json) and [`screenshots/`](screenshots/). Captures
cover desktop 1440x1000 and mobile 375x812. The script asserts no horizontal
overflow and no JavaScript page errors for the exercised flows.

The submission PDF is rendered and visually inspected after generation. Layout
checks cover page boundaries, readable code/table wrapping and source links.
PDF generation/QA dependencies are separate from the application runtime.

## Reproduction limits

CPU latency varies with hardware and background load. The local model cache is
not committed; use the checksum-pinned setup helper. The live examples depend on
the supplied fixture and current store-local date. For the illustrated
2026-10-27 receipt, the four-day outcome is specific to the case date 2026-10-31;
automated date-boundary tests freeze that date. A later real demo should use a
recent actual receipt date to demonstrate the same rule honestly.
