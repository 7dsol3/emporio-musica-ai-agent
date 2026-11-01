import json
import threading
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from emporio.service import AgentService


def test_native_function_calling_contract(settings):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            body = json.dumps({"choices": [{"message": {"tool_calls": [{"function": {
                "name": "get_product", "arguments": '{"product_id":95}'}}]}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        configured = replace(settings, provider="openai_compatible", model="contract-test-stub",
                             model_url=f"http://127.0.0.1:{server.server_port}/v1/chat/completions")
        agent = AgentService(configured)
        result = agent.turn("Price for Takamine GD20? My email is private@example.com")
        assert result["mode"] == "openai_compatible" and "2,199.00" in result["message"]
        assert "private@example.com" not in json.dumps(received)
        assert received[0]["tools"] and received[0]["tool_choice"] == "required"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_provider_failure_falls_back_without_leaking_secret(settings, monkeypatch):
    configured = replace(settings, provider="openai_compatible", model="stub",
                         model_url="http://127.0.0.1:1/v1/chat/completions", model_key="do-not-log-this")
    agent = AgentService(configured)
    def fail(*args):
        raise RuntimeError("do-not-log-this")
    monkeypatch.setattr(agent.model, "plan", fail)
    result = agent.turn("How much is Takamine GD20?")
    assert result["mode"] == "local_fallback" and "2,199.00" in result["message"]
    assert "do-not-log-this" not in json.dumps(result)


def test_model_cannot_invent_receipt_date_or_item_condition(settings, monkeypatch):
    from emporio.planner import Call, Plan
    from datetime import date
    configured = replace(settings, provider="openai_compatible", model="stub", model_url="http://127.0.0.1:1/v1/chat/completions")
    agent = AgentService(configured)
    monkeypatch.setattr(agent.model, "plan", lambda *args: Plan([Call("assess_return", {"channel": "online", "received_date": "2026-10-30", "condition": "unused"})], mode="openai_compatible"))
    result = agent.turn("I want to return my online purchase", today=date(2026, 10, 31))
    assert result["results"][0]["status"] == "needs_information"


def test_model_cannot_repeat_catalog_instead_of_selected_product(settings, monkeypatch):
    from emporio.planner import Call, Plan
    configured = replace(settings, provider="openai_compatible", model="stub", model_url="http://127.0.0.1:1/v1/chat/completions")
    agent = AgentService(configured)
    session = agent.store.session()
    session["context"]["last_products"] = [83, 85, 89]
    agent.store.save_session(session)
    monkeypatch.setattr(agent.model, "plan", lambda *args: Plan([Call("search_products", {"query": "acoustic guitar", "category_id": 5})], mode="openai_compatible"))
    result = agent.turn("Tell me about the first one", session["id"])
    assert result["mode"] == "local_fallback"
    assert result["results"][0]["products"][0]["id"] == 83
    assert len(result["results"][0]["products"]) == 1


def test_model_cannot_drop_requested_opening_hours(settings, monkeypatch):
    from emporio.planner import Call, Plan
    configured = replace(settings, provider="openai_compatible", model="stub", model_url="http://127.0.0.1:1/v1/chat/completions")
    agent = AgentService(configured)
    monkeypatch.setattr(agent.model, "plan", lambda *args: Plan([Call("search_policies", {"query": "store address", "topic": "about"})], mode="openai_compatible"))
    result = agent.turn("What are the address and opening hours of the store?")
    assert result["mode"] == "local_fallback"
    assert "09:00-18:00" in result["message"] and "Rua 14 de Maio" in result["message"]
