from __future__ import annotations

import json
import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .policies import PolicyBook, normalize
from .storage import Store, cents


class Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SearchProducts(Arguments):
    query: str = Field(default="", max_length=160)
    category_id: int | None = Field(default=None, ge=1, le=9)
    max_price_brl: str | None = Field(default=None, max_length=20)
    available_only: bool = True
    limit: int = Field(default=5, ge=1, le=8)


class GetProduct(Arguments):
    product_id: int = Field(ge=1)


class SearchPolicies(Arguments):
    query: str = Field(min_length=1, max_length=300)
    topic: str | None = Field(default=None, max_length=30)


class GetOrder(Arguments):
    order_id: int = Field(ge=1)


class QuotePayment(Arguments):
    product_id: int = Field(ge=1)
    method: Literal["pix", "credit", "debit", "boleto"] = "pix"
    installments: int = Field(default=1, ge=1, le=12)
    quantity: int = Field(default=1, ge=1, le=20)


class AssessReturn(Arguments):
    channel: Literal["online", "store", "unknown"] = "unknown"
    received_date: str | None = Field(default=None, max_length=10)
    condition: Literal["unused", "used", "unknown"] = "unknown"
    exception: bool = False


class QuoteShipping(Arguments):
    total_brl: str = Field(max_length=20)
    metro_campo_grande: bool


TOOL_MODELS = {"search_products": SearchProducts, "get_product": GetProduct,
               "search_policies": SearchPolicies, "get_order": GetOrder,
               "quote_payment": QuotePayment, "assess_return": AssessReturn,
               "quote_shipping": QuoteShipping}

TOOL_DESCRIPTIONS = {
    "search_products": "Search the current catalog by model name/category and optional BRL budget. An acoustic guitar/violão is category 5; electric guitar 1; keyboard 4; ukulele 9.",
    "get_product": "Read one product by its known ID, including current price, active promotion and availability.",
    "search_policies": "Retrieve store policies, contact information, opening hours, warranty, delivery, privacy, returns or human support.",
    "get_order": "Read an order subject to server-side verified customer scope. Never infer identity or ask for passwords. No customer_id argument is accepted.",
    "quote_payment": "Compute nonstacking PIX/promotion prices or check installment rules for a known product.",
    "assess_return": "Evaluate the manual's online change-of-mind window using an explicitly stated actual received_date in ISO format. Never use order_date or estimated_delivery as receipt.",
    "quote_shipping": "Quote the manual's metropolitan delivery fee; exactly BRL 500 needs human review. Other cities need a carrier quote.",
}


def tool_schemas() -> list[dict]:
    return [{"type": "function", "function": {"name": name, "description": TOOL_DESCRIPTIONS[name],
            "parameters": model.model_json_schema()}} for name, model in TOOL_MODELS.items()]


def money(amount_cents: int) -> str:
    return f"BRL {amount_cents / 100:,.2f}"


class Tools:
    def __init__(self, store: Store, policies: PolicyBook):
        self.store, self.policies = store, policies

    def execute(self, name: str, arguments: dict, customer_id: int | None = None,
                today: date | None = None) -> dict:
        if name not in TOOL_MODELS:
            raise ValueError("Unknown tool")
        args = TOOL_MODELS[name].model_validate(arguments).model_dump()
        if name == "get_order":
            return self.get_order(args["order_id"], customer_id)
        if name == "assess_return":
            return self.assess_return(**args, today=today or date.today())
        return getattr(self, name)(**args)

    def _product(self, row) -> dict:
        value = dict(row)
        discount = int(value.pop("discount", 0) or 0)
        value["discount_percent"] = discount
        value["sale_cents"] = int((Decimal(value["price_cents"]) * (100-discount) / 100)
                                  .quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        value["available"] = value["status"] == "active" and value["stock"] > 0
        value["specs"] = json.loads(value["specs"])
        return value

    def search_products(self, query="", category_id=None, max_price_brl=None,
                        available_only=True, limit=5) -> dict:
        max_cents = cents(max_price_brl) if max_price_brl is not None else None
        with self.store.connect() as db:
            rows = db.execute("""SELECT p.*, c.name AS category,
                COALESCE((SELECT MAX(discount_percent) FROM promotions WHERE product_id=p.id AND active=1),0) AS discount
                FROM products p JOIN categories c ON c.id=p.category_id ORDER BY p.price_cents,p.id""").fetchall()
        tokens = re.findall(r"[a-z0-9]+", normalize(query))
        values = [self._product(r) for r in rows]
        selected = [p for p in values
                    if (category_id is None or p["category_id"] == category_id)
                    and (not available_only or p["available"])
                    and (max_cents is None or p["sale_cents"] <= max_cents)
                    and all(token in normalize(p["name"] + " " + p["description"]) for token in tokens)]
        selected.sort(key=lambda p: (p["sale_cents"], p["id"]))
        products = selected[:limit]
        return {"kind": "catalog", "products": products, "total_matches": len(selected),
                "sources": [{"id": f"product:{p['id']}", "label": f"Catalog, product #{p['id']}", "type": "catalog"} for p in products],
                "snapshot": "Supplied CSV snapshot; not a live inventory integration."}

    def get_product(self, product_id: int) -> dict:
        with self.store.connect() as db:
            row = db.execute("""SELECT p.*,c.name AS category,
                COALESCE((SELECT MAX(discount_percent) FROM promotions WHERE product_id=p.id AND active=1),0) AS discount
                FROM products p JOIN categories c ON c.id=p.category_id WHERE p.id=?""", (product_id,)).fetchone()
        if row is None:
            return {"kind": "catalog", "products": [], "total_matches": 0, "sources": []}
        p = self._product(row)
        alternatives = []
        if not p["available"]:
            alternatives = self.search_products(category_id=p["category_id"], limit=3)["products"]
        return {"kind": "catalog", "products": [p], "total_matches": 1, "alternatives": alternatives,
                "sources": [{"id": f"product:{x['id']}", "label": f"Catalog, product #{x['id']}", "type": "catalog"} for x in [p, *alternatives]]}

    def search_policies(self, query: str, topic: str | None = None) -> dict:
        return self.policies.search(query, topic)

    def get_order(self, order_id: int, customer_id: int | None) -> dict:
        if customer_id is None:
            return {"kind": "order", "status": "verification_required", "sources": []}
        with self.store.connect() as db:
            row = db.execute("SELECT id,order_date,status,total_cents,payment_method,tracking_code,estimated_delivery FROM orders WHERE id=? AND customer_id=?",
                             (order_id, customer_id)).fetchone()
            if row is None:
                return {"kind": "order", "status": "unavailable", "sources": []}
            items = db.execute("SELECT i.product_id,i.quantity,p.name FROM order_items i JOIN products p ON p.id=i.product_id WHERE order_id=?", (order_id,)).fetchall()
        return {"kind": "order", "status": "found", "order": dict(row), "items": [dict(i) for i in items],
                "sources": [{"id": f"order:{order_id}", "label": f"Verified order #{order_id}", "type": "order"}]}

    def quote_payment(self, product_id: int, method="pix", installments=1, quantity=1) -> dict:
        result = self.get_product(product_id)
        if not result["products"]:
            return {"kind": "payment", "status": "not_found", "sources": []}
        p = result["products"][0]
        sources = result["sources"][:1] + self.policies.search("payment", "payments")["sources"]
        if not p["available"] or quantity > p["stock"]:
            return {"kind": "payment", "status": "unavailable", "sources": sources}
        discount = p["discount_percent"] or (5 if method == "pix" else 0)
        total = int((Decimal(p["price_cents"] * quantity) * (100-discount) / 100)
                    .quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        minimum = 5000 if installments <= 3 else 8000 if installments <= 6 else 10000
        allowed = method != "credit" and installments == 1 or method == "credit" and (installments == 1 or total // installments >= minimum)
        valid_counts = [n for n in range(1, 13) if n == 1 or total // n >= (5000 if n <= 3 else 8000 if n <= 6 else 10000)]
        return {"kind": "payment", "status": "quoted", "product": p["name"], "quantity": quantity,
                "method": method, "list_total_cents": p["price_cents"] * quantity,
                "total_cents": total, "discount_percent": discount, "promotion_applied": bool(p["discount_percent"]),
                "installments": installments, "allowed": allowed, "allowed_installments": valid_counts,
                "installment_floor_cents": total // installments,
                "installment_remainder_cents": total % installments, "sources": sources}

    def assess_return(self, channel="unknown", received_date=None, condition="unknown", exception=False, today=None) -> dict:
        sources = self.policies.search("return", "returns")["sources"]
        missing = []
        if channel == "unknown":
            missing.append("whether the purchase was online or in store")
        if not received_date:
            missing.append("the actual date you received the item (YYYY-MM-DD)")
        if condition == "unknown":
            missing.append("whether the item is unused, with original packaging and all included materials")
        if missing:
            return {"kind": "return", "status": "needs_information", "missing": missing, "sources": sources}
        received = date.fromisoformat(received_date)
        elapsed = ((today or date.today()) - received).days
        if elapsed < 0:
            return {"kind": "return", "status": "invalid_date", "sources": sources}
        if exception or channel == "store" or condition == "used" or elapsed > 7:
            return {"kind": "return", "status": "human_review", "days_since_receipt": elapsed, "sources": sources}
        return {"kind": "return", "status": "within_policy_window", "days_since_receipt": elapsed,
                "sources": sources, "notice": "Preliminary policy guidance, not a refund authorization."}

    def quote_shipping(self, total_brl: str, metro_campo_grande: bool) -> dict:
        amount = cents(total_brl)
        sources = self.policies.search("delivery", "delivery")["sources"]
        if not metro_campo_grande:
            return {"kind": "shipping", "status": "carrier_quote_required", "sources": sources}
        if amount == 50000:
            return {"kind": "shipping", "status": "boundary_review", "sources": sources}
        return {"kind": "shipping", "status": "quoted", "fee_cents": 0 if amount > 50000 else 3500,
                "estimate": "1-3 business days; policy estimate only", "sources": sources}
