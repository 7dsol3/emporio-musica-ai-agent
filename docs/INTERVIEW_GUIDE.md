# Interview preparation

## Explain the design in one minute

The store needs accurate answers to repetitive questions, so the design separates
structured operational facts from document policies. Python tools query prices,
stock, promotions and ownership-scoped orders. A page-aware Konaet retrieval
component indexes the small policy PDF. A local language model selects bounded
functions, while deterministic rules calculate prices and apply explicit policy
conditions. Source receipts make the result inspectable, and a local router
keeps common flows available if model planning fails.

## Demonstrate the implementation

1. Start `Run Demo.cmd` and keep English selected.
2. Ask for acoustic guitars under BRL 1,000, choose the first result and request
   12 installments. Explain the tier minimum rather than promising every count.
3. Ask about Taylor 110e, then PIX. Show the active 8% offer and the rule that
   prevents adding another 5% discount.
4. Start a return without receipt details, then provide an explicit recent actual
   receipt date and original condition. Explain why an estimated date is insufficient.
5. Request order 8 before verification, verify the fictional identity through
   the separate form, then request order 1 to show ownership isolation.
6. Switch to Portuguese to demonstrate the same tools and numeric facts in the
   Brazilian customer language. Keep submitted examples/documentation in English.

## Files to understand

- `service.py`: turn orchestration, model fallback and trusted fact boundaries.
- `planner.py`: local extraction and the native function-calling adapter.
- `tools.py`: typed schemas, parameterized queries and business calculations.
- `storage.py`: transactional ingestion, sessions, ownership and audit records.
- `policies.py`: PDF indexing, reviewed summaries and manual version guard.
- `api.py`: request/session boundary and verification endpoint.
- `tests/`: meaningful assertions for money, dates, identity and model failure.

## Questions worth practicing

**Why not a vector database?** The manual has only eight pages. FTS5 and topic
expansion are easy to reproduce and inspect. A larger heterogeneous corpus could
justify hybrid semantic retrieval after measuring recall and operating costs.

**Is the assistant an LLM?** The full demo has an actual external local Qwen
model for function selection. Konaet supplies orchestration and a reused
retrieval module. The offline mode is an explicit deterministic router. The two
modes must not be confused in a demo or capability claim.

**How is hallucination controlled?** The model cannot execute arbitrary code,
write financial state, select a customer scope or provide final unsupported facts.
Validated tool results feed the renderer. It can still choose a poor search
query; broader intent evaluation and a stronger model would improve that limit.

**What changes for production?** Strong customer authentication, authenticated
store/carrier APIs, reviewed policies, shared storage/rate limits, encrypted
operations, monitoring, accessibility review and measured concurrency/latency.

**What did coding assistance do?** Answer consistently with the README's factual
workflow disclosure. Explain the implementation and reproduced results in your
own words; do not claim work or checks that you have not personally understood.
