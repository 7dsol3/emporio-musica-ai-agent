# Data decisions and unresolved policy details

## Original inputs

The six supplied CSVs contain 9 categories, 65 products, 50 customers, 20 orders,
22 item rows and 25 promotions. The policy manual has eight PDF pages and is
version 2.1, June 2025. The source files are preserved unchanged. Runtime source
hashes are available through `python -m emporio ingest`.

Only IDs and normalized purchase emails are imported from the customer table.
All other customer fields are excluded from the operational database. Dates,
monetary values, product status, JSON specs, promotion flags and relational
references are validated before a source replacement commits.

## Interpretations

| Evidence | Decision |
| --- | --- |
| Product has zero stock, discontinued or coming-soon status | Do not offer it as available. Suggest available category alternatives for a direct product lookup. |
| Promotion table has `is_active`, but no validity dates | Treat only the flag as current for the supplied snapshot; never infer dates from campaign names. |
| More than one active offer could apply | Select the largest single discount; never sum discounts. |
| PIX rule and promotional pricing | Apply 5% only to list price when there is no active promotional price. |
| Installment table says BRL 100 generally; detailed section gives tiers | Use detailed tiers: 1-3 installments minimum BRL 50, 4-6 minimum BRL 80, 7-12 minimum BRL 100. A single payment is always allowed. The first tier's wording is an interpretation requiring store confirmation before production. |
| Monetary division does not divide exactly | Allocate the remainder as one additional cent to the necessary number of installments; the sum equals the total. |
| Local shipping says above/below BRL 500 | Exactly BRL 500 is undefined and requires staff confirmation. |
| Mixed payment is allowed above BRL 2,000 | Preserve the strict above boundary; this prototype explains the policy but does not execute split payment. |
| Return window starts at receipt | Ask for actual receipt. Order date, delivered status and estimated delivery are not substitutes. |
| Online-return conditions and exclusions | Provide preliminary guidance; personalized, used, final-sale, in-store or late requests go to human review, not an automatic denial. |
| 30-day exchange section and 90-day warranty section | Describe the separate sections and escalate uncertainty. Do not erase the 90-day provision because 30 days passed. |
| Conflicting WhatsApp numbers in cover/company details and section 7 | Quote the consistent general telephone, and ask the team to confirm WhatsApp. |
| Accented/unaccented email variants in the manual | Avoid choosing an unverified email address in customer replies; the general phone and address remain available. |
| Historic totals for orders 3 and 20 differ from current catalog arithmetic | Keep the recorded order totals. The input contains no historical item-price ledger. |
| Tracking code examples differ from some stored records | Show the supplied recorded code only after verification; do not fabricate or normalize it into an invented carrier code. |
| Delayed/stale order estimates | Label them as recorded snapshot estimates; no live carrier status is inferred. |

## Time

Store schedule calculations use Campo Grande, UTC-04:00, rather than São Paulo
time. Regular weekday/Saturday hours come from the manual. The 2026 national
holiday list follows the [official MGI calendar](https://agenciagov.ebc.com.br/noticias/202512/confira-o-calendario-oficial-de-feriados-nacionais-e-pontos-facultativos-em-2026).
Municipal and special closures are not established by that source and must be
confirmed. A next opening is labeled scheduled, not guaranteed.

The repository and English examples use the case date, 2026-10-31, when describing
the return-window demonstration. Automated tests freeze that date explicitly;
normal application turns use the current store-local date.
