from datetime import date

import pytest

from emporio.storage import cents


def test_fixture_import_is_idempotent_and_minimizes_customer_fields(agent):
    first = agent.data_report
    assert first["counts"]["products"] == 65
    assert first["counts"]["orders"] == 20
    assert agent.store.import_data(agent.settings.data_dir) == first
    with agent.store.connect() as db:
        assert [r["name"] for r in db.execute("PRAGMA table_info(customers)")] == ["id", "email"]


@pytest.mark.parametrize("value,expected", [("599.9", 59990), ("1.005", 101), ("0", 0)])
def test_money_rounding(value, expected):
    assert cents(value) == expected


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1"])
def test_invalid_money_rejected(value):
    with pytest.raises(ValueError):
        cents(value)


def test_catalog_budget_and_sql_injection(agent):
    result = agent.tools.execute("search_products", {"category_id": 5, "max_price_brl": "1000"})
    assert result["products"]
    assert all(p["available"] and p["sale_cents"] <= 100000 and p["category_id"] == 5 for p in result["products"])
    assert not agent.tools.execute("search_products", {"query": "' OR 1=1 --"})["products"]
    with agent.store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 65


def test_english_catalog_category_from_language_model(agent):
    result = agent.tools.execute("search_products", {"query": "acoustic guitar", "category_id": 5, "max_price_brl": "1000"})
    assert result["products"] and all(p["category_id"] == 5 for p in result["products"])


def test_prices_and_stock_are_read_again_on_each_turn(agent):
    before = agent.tools.get_product(81)["products"][0]
    with agent.store.connect() as db:
        db.execute("UPDATE products SET stock=0,price_cents=77777 WHERE id=81")
    after = agent.tools.get_product(81)["products"][0]
    assert before["price_cents"] != after["price_cents"]
    assert after["price_cents"] == 77777 and not after["available"]
    assert agent.tools.get_product(81)["alternatives"]


def test_discontinued_and_coming_soon_are_never_available(agent):
    with agent.store.connect() as db:
        ids = [r[0] for r in db.execute("SELECT id FROM products WHERE status!='active'")]
    assert len(ids) == 3
    for product_id in ids:
        assert not agent.tools.get_product(product_id)["products"][0]["available"]


def test_active_promo_cannot_stack_with_pix(agent):
    quote = agent.tools.execute("quote_payment", {"product_id": 94, "method": "pix"})
    assert quote["promotion_applied"] and quote["discount_percent"] == 8
    assert quote["list_total_cents"] == 599900
    assert quote["total_cents"] == 551908


def test_inactive_promo_is_not_offered(agent):
    assert agent.tools.get_product(95)["products"][0]["discount_percent"] == 0
    quote = agent.tools.execute("quote_payment", {"product_id": 95, "method": "pix"})
    assert quote["discount_percent"] == 5 and quote["total_cents"] == 208905


def test_installment_tiers_and_exact_rounding(agent):
    quote = agent.tools.execute("quote_payment", {"product_id": 127, "method": "credit", "installments": 6})
    assert not quote["allowed"] and quote["allowed_installments"] == [1, 2, 3, 4]
    quote = agent.tools.execute("quote_payment", {"product_id": 127, "method": "credit", "installments": 3})
    assert quote["allowed"]
    assert quote["installment_floor_cents"] * 3 + quote["installment_remainder_cents"] == quote["total_cents"]


@pytest.mark.parametrize("amount,fee", [("499.99", 3500), ("500.01", 0)])
def test_shipping_defined_boundaries(agent, amount, fee):
    assert agent.tools.execute("quote_shipping", {"total_brl": amount, "metro_campo_grande": True})["fee_cents"] == fee


def test_shipping_exactly_500_is_escalated(agent):
    result = agent.tools.execute("quote_shipping", {"total_brl": "500", "metro_campo_grande": True})
    assert result["status"] == "boundary_review" and "fee_cents" not in result


@pytest.mark.parametrize("received,status", [("2026-10-24", "within_policy_window"), ("2026-10-23", "human_review"), ("2026-11-01", "invalid_date")])
def test_return_seven_calendar_day_boundary(agent, received, status):
    result = agent.tools.execute("assess_return", {"channel": "online", "received_date": received, "condition": "unused"}, today=date(2026, 10, 31))
    assert result["status"] == status


def test_return_missing_receipt_does_not_use_estimated_delivery(agent):
    result = agent.tools.execute("assess_return", {"channel": "online"})
    assert result["status"] == "needs_information"
    assert any("actual date" in missing for missing in result["missing"])


def test_policy_retrieval_has_actual_pdf_page_provenance(agent):
    result = agent.tools.execute("search_policies", {"query": "What is the warranty?"})
    assert result["found"] and result["retrieval"]
    assert any(s["page"] == 7 and s["sha256"] == agent.policies.sha for s in result["sources"])
    assert "90-day" in result["cards"][0]["summary"]


def test_no_customer_scope_can_be_injected(agent):
    with pytest.raises(ValueError):
        agent.tools.execute("get_order", {"order_id": 1, "customer_id": 3})
    with pytest.raises(ValueError):
        agent.tools.execute("execute_sql", {"sql": "SELECT * FROM customers"})


def test_order_ownership_and_historical_total(agent):
    assert agent.tools.get_order(8, None)["status"] == "verification_required"
    session = agent.store.session()
    assert agent.store.verify_order(session, 8, "ANACAROL.FERREIRA@COLDMAIL.COM")
    assert agent.tools.get_order(8, session["customer_id"])["status"] == "found"
    assert agent.tools.get_order(1, session["customer_id"])["status"] == "unavailable"
    order = agent.tools.get_order(3, 12)["order"]
    assert order["total_cents"] == 345000
    assert "customer_id" not in order and "email" not in order


def test_wrong_verification_clears_prior_authorization(agent):
    session = agent.store.session()
    assert agent.store.verify_order(session, 8, "anacarol.ferreira@coldmail.com")
    assert not agent.store.verify_order(session, 1, "wrong@example.com")
    assert agent.store.session(session["id"])["customer_id"] is None


def test_audit_survives_restart_and_detects_tampering(agent):
    from emporio.storage import Store
    agent.store.audit("session", "test", ["product:81"], "checked")
    restarted = Store(agent.store.path)
    restarted.audit("session", "test2", [], "checked")
    assert restarted.verify_audit()["valid"] and restarted.verify_audit()["records"] == 2
    with restarted.connect() as db:
        db.execute("UPDATE audit SET payload='{}' WHERE seq=1")
    assert not restarted.verify_audit()["valid"]
