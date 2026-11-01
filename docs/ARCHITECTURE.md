# Architecture and execution boundaries

## A turn from input to evidence

1. FastAPI validates the message and language, resolves an HttpOnly session
   cookie, applies a client rate limit and rejects unexpected origins/hosts.
2. The local router identifies common store needs and extracts explicit facts.
   A configured language model can select native function calls through the
   same bounded interface. Greetings and rejected scope bypass model inference.
3. Pydantic validates the allowlisted function name and arguments. At most three
   tool calls are accepted in one planning round. No generated SQL or code executes.
4. Transaction-related arguments must agree with explicit local extraction.
   Return facts come from the customer's stated context, never invented model values.
5. Structured tools query SQLite with parameters. Order ownership is supplied by
   the trusted session and applied inside the order query, not by model instruction.
6. Policy tools combine PDF-derived FTS retrieval with version-pinned reviewed
   summaries and deterministic business rules. Each answer carries source IDs/pages.
7. The renderer creates an English or Portuguese answer from those results.
   Model free text cannot become a price, delivery promise or refund approval.
8. The application saves bounded, redacted conversation context and an atomic
   hash-linked audit receipt. The response identifies model/local/fallback mode.

## Tools

| Function | Boundary |
| --- | --- |
| `search_products` | Model/brand/category/budget filters, available-only default, at most eight displayed results |
| `get_product` | Price, active promotion, lifecycle status and alternatives for one recorded product |
| `search_policies` | Store information and policy summaries, original PDF page references and retrieval metadata |
| `get_order` | Session-scoped recorded order information; no customer-ID argument or list-all operation |
| `quote_payment` | Integer-cent discounts, no stacking, quantity/stock checks and installment tiers |
| `assess_return` | Explicit actual receipt date, purchase channel and condition; preliminary guidance only |
| `quote_shipping` | Defined metropolitan fee rules; exactly BRL 500 and other cities require review/quote |

The HTTP API does not expose arbitrary tools directly. The catalog endpoint is
public; order information is available only through the ownership-checked agent.
There is no customer-table endpoint. The original fictional manual is available
at `/manual` so customers/reviewers can follow page references.

## Retrieval and source freshness

`emporio/vendor/konaet_knowledge.py` is the unchanged, frozen Konaet retrieval
component. It uses SQLite FTS5 `unicode61 remove_diacritics 2`, page-preserving
chunks, BM25 ranking and AND-then-OR query fallback. Application topic expansion
maps common English questions onto the Portuguese source vocabulary.

The curated cards complement lexical retrieval for this eight-page manual.
They are not automatically generated rules. Each card cites the complete
relevant pages; source text is interpreted as reference data, not executable
instructions. A pinned PDF hash prevents a source update from silently leaving
the cards stale. This is a deliberate small-corpus design, not a claim that a
generic RAG engine can resolve policy contradictions automatically.

CSV hashes, row counts and data warnings are recorded during transactional
ingestion. A changed source set is replaced atomically on startup. Queries read
the imported snapshot each turn, so committed database updates are visible;
editing a CSV requires restarting/reimporting. Importing data does not train a model.

## Model boundary

The full Windows demo downloads official Qwen3-0.6B Q8_0 weights and a pinned
llama.cpp CPU server. The adapter sends tool definitions, a store system prompt,
redacted recent user turns and minimal public context. Verified identity data,
tool outputs and assistant order-detail history remain outside that prompt.

Qwen is separate from Konaet's orchestration and retrieval code. No external
model is renamed as a proprietary Konaet model. No Cauryvo checkpoint was
available in the inspected workspace; unrelated ARC/anti-cheat models were not
treated as conversational models.

The protocol adapter is tested with a labeled stub and with a real local server.
A model can still choose a poor retrieval query. Argument validation controls
capability and data access, not semantic correctness of every intent; that limit
is reflected in the evaluation and local fallback strategy.

## Operational tradeoffs

SQLite WAL and parameterized reads keep setup small. Audit insertion uses
`BEGIN IMMEDIATE` so sequence/hash updates are atomic. A process-wide turn lock
prevents simultaneous requests from overwriting the same conversational context,
at the cost of serializing turns. This is appropriate to a local prototype;
it is not a multi-tenant production architecture.

State and model artifacts live under ignored `var/`. The model helper starts
its background server without a separate Windows console and terminates the
child when the application exits. It binds both services to loopback. No
automatic message, payment, public deployment or form submission occurs.
