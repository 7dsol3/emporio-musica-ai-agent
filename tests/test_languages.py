from datetime import date

from fastapi.testclient import TestClient

from emporio.api import create_app


def test_default_english_and_optional_portuguese_share_facts(agent):
    english = agent.turn("How much is Takamine GD20?")
    portuguese = agent.turn("Quanto custa o Takamine GD20?", locale="pt")
    assert english["locale"] == "en" and "BRL 2,199.00" in english["message"]
    assert portuguese["locale"] == "pt" and "R$ 2.199,00" in portuguese["message"]
    assert english["results"] == portuguese["results"]


def test_portuguese_return_and_policy(agent):
    reply = agent.turn("Quero devolver minha compra online", locale="pt", today=date(2026, 10, 31))
    assert "data real" in reply["message"]
    reply = agent.turn("Recebi em 2026-10-27. Está sem uso, na embalagem original com todos os manuais.", reply["session_id"], locale="pt", today=date(2026, 10, 31))
    assert "4 dias" in reply["message"] and "Nenhuma devolução" in reply["message"]
    policy = agent.turn("Qual o horário de funcionamento?", locale="pt")
    assert "segunda a sexta" in policy["message"]


def test_api_language_selection_is_validated(settings):
    with TestClient(create_app(settings)) as client:
        assert client.post("/api/chat", json={"message": "Olá", "locale": "pt"}).json()["message"].startswith("Olá!")
        assert client.post("/api/chat", json={"message": "Hi", "locale": "xx"}).status_code == 422
        assert client.get("/api/policies?locale=pt").json()[0]["title"] == "Loja e contato"
