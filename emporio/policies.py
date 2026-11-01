from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

from .vendor.konaet_knowledge import KnowledgeBase, sha256_file


# English editorial summaries of the supplied fictional manual, not legal advice.
# Page numbers refer to PDF pages, including its cover.
CARDS = {
    "about": ("Store and contact", [1, 2],
        "Empório da Música sells musical instruments in Campo Grande, MS. Address: Rua 14 de Maio, 3200, Centro, Campo Grande - MS, CEP 79202-333. General telephone: (67) 3341-4444. The manual lists conflicting WhatsApp numbers; ask the team to confirm that channel. Accessories, cables, strings, picks, cases, pedals and amplifiers are outside the catalog."),
    "hours": ("Opening hours", [2, 6],
        "The human team is available Monday to Friday, 09:00-18:00, and Saturday, 09:00-13:00, in Campo Grande local time (UTC-04:00). The store is closed on Sundays and public holidays. Special opening hours must be confirmed with the team. The virtual assistant can answer outside those hours."),
    "payments": ("Payment methods and installments", [3, 6],
        "PIX gives 5% off the list price, except on promotional prices. Debit and boleto are accepted; boleto clearing can take up to 3 business days. Interest-free credit installments: 1-3 payments with a BRL 50 minimum installment, 4-6 with BRL 80 minimum, and 7-12 with BRL 100 minimum. The detailed installment rules take precedence over the table's general BRL 100 statement. Split payment is allowed only on purchases above BRL 2,000. Promotions and PIX discounts cannot be stacked."),
    "returns": ("Returns and exchanges", [4, 7],
        "For an online purchase, a change-of-mind return can be requested within 7 calendar days after actual receipt. The manual requests original packaging, no signs of use, all accessories and manuals. The store pays return freight and states a refund within 10 business days using the original payment method. Preference exchanges are described within 7 days, subject to stock and original condition. Personalized instruments and final-sale items require staff review. Manufacturing defects are described under a 30-day exchange process and a separate 90-day legal-warranty section; the assistant must escalate uncertainty and must not deny warranty just because 30 days passed. Estimated delivery is not proof of receipt."),
    "delivery": ("Shipping and tracking", [4, 5],
        "Within metropolitan Campo Grande, orders above BRL 500 have free shipping; orders below BRL 500 have a BRL 35 fee, with an estimate of 1-3 business days. The manual leaves exactly BRL 500 unspecified, so the team must confirm that boundary. Other cities: PAC 5-12, SEDEX 2-5, or Jadlog 3-8 business days; the price needs destination, weight and dimensions. Large instruments may need a special quote. These are policy estimates, not a newly confirmed delivery date. Tracking is sent after dispatch. Refuse a damaged delivery and contact the store promptly."),
    "promotions": ("Promotions", [6, 7],
        "Only promotions marked active in the current supplied system snapshot may be quoted. Discounts do not stack. The 5% PIX discount does not apply to an already promotional price. Show original price, discount percentage and final price together. Offers are subject to available stock; an inactive offer must not be promised. The CSV supplies an active flag but no start or end dates."),
    "warranty": ("Warranty", [4, 7],
        "The manual states a 90-day legal warranty for manufacturing defects from receipt, plus a manufacturer warranty that can range from 6 months to 2 years, subject to the product's certificate. Its exchange procedure also mentions 30 days from purchase; refer conflicts to the team instead of denying coverage. Wear, misuse, falls, extreme conditions and unauthorized repairs are listed as exclusions requiring case review."),
    "privacy": ("Privacy", [7, 8],
        "Customer information is used for order processing, delivery, order communication and legal duties. Marketing requires explicit consent; customer information is not shared for third-party marketing. Data deletion can be requested from the team. This prototype minimizes stored customer data and never exposes the customer table through the agent."),
    "handoff": ("Human support", [7, 8],
        "Complaints and unclear policy applications should be referred to the human team. The manual states a response within 24 business hours. General telephone: (67) 3341-4444. The assistant can prepare a local handoff summary, but this prototype has no connected ticketing or messaging service and cannot claim that a request was sent."),
}

KEYWORDS = {
    "about": "address endereco loja store located location telefone phone contact contato accessory accessories acessorio cordas palhetas cabos amplificador pedal cases",
    "hours": "hours opening horario funcionamento abre aberto open fecha closed sabado sunday domingo feriado holiday",
    "payments": "payment pagamento pagar pay installment installments parcela parcelamento credit credito debit debito boleto pix juros interest split",
    "returns": "return returns devolver devolucao arrependimento refund reembolso exchange troca trocar damaged avaria defeito defect recebido received receipt",
    "delivery": "shipping delivery entrega frete tracking rastreio rastreamento sedex pac jadlog prazo cep metropolitan",
    "promotions": "promotion promotions promocao promo desconto discount oferta black friday",
    "warranty": "warranty garantia fabricante manufacturer repair reparo",
    "privacy": "privacy privacidade dados data lgpd personal pessoal consent consentimento excluir deletar",
    "handoff": "human humano attendant atendente complaint reclamacao reclamar falar pessoa manager gerente suporte support",
}


def normalize(text: str) -> str:
    import unicodedata
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", text.casefold())
                            if not unicodedata.combining(c)).split())


def topics_for(query: str) -> list[str]:
    words = set(re.findall(r"[a-z0-9]+", normalize(query)))
    scores = [(len(words & set(keywords.split())), topic) for topic, keywords in KEYWORDS.items()]
    scores.sort(key=lambda item: -item[0])
    return [topic for score, topic in scores if score > 0][:3]


class PolicyBook:
    def __init__(self, data_dir: Path, db_path: Path):
        self.path = data_dir / "políticas_da_loja.pdf"
        self.sha = sha256_file(self.path)
        self.knowledge = KnowledgeBase(db_path)
        existing = self.knowledge.list_documents()
        if not existing or any(doc.source_sha256 != self.sha for doc in existing):
            with self.knowledge._connect() as db:
                db.execute("DELETE FROM knowledge_fts")
                db.execute("DELETE FROM knowledge_documents")
            reader = PdfReader(self.path)
            self.knowledge.import_pages(
                title="Empório da Música - Store policies, version 2.1",
                source_name=self.path.name, source_sha256=self.sha,
                rights="Fictional technical-case material supplied for evaluation; not relicensed.",
                pages=[(i, re.sub(r"\s+", " ", page.extract_text() or "").strip())
                       for i, page in enumerate(reader.pages, 1)])

    def search(self, query: str, topic: str | None = None) -> dict:
        topics = [topic] if topic in CARDS else topics_for(query)
        if not topics:
            return {"kind": "policy", "cards": [], "sources": [], "found": False}
        # English queries are expanded with the manual's Portuguese terminology.
        expansion = " ".join(KEYWORDS[t] for t in topics)
        hits = self.knowledge.search(expansion, limit=5)
        cards, sources = [], []
        for key in topics:
            title, pages, text = CARDS[key]
            cards.append({"topic": key, "title": title, "summary": text})
            sources.extend({"id": f"policy:p{page}", "label": f"Store policies, p. {page}",
                            "page": page, "sha256": self.sha, "type": "policy"} for page in pages)
        return {"kind": "policy", "found": True, "cards": cards,
                "sources": list({s["id"]: s for s in sources}.values()),
                "retrieval": [{"page": h.page, "score": h.score} for h in hits]}
