from fastapi.testclient import TestClient

from emporio.api import create_app


def test_api_session_verification_and_reset(settings):
    with TestClient(create_app(settings)) as client:
        session = client.get("/api/session")
        assert session.status_code == 200
        assert "httponly" in session.headers["set-cookie"].lower()
        assert "samesite=strict" in session.headers["set-cookie"].lower()
        response = client.post("/api/chat", json={"message": "Where is order 8?"})
        assert response.json()["results"][0]["status"] == "verification_required"
        assert client.post("/api/verify", json={"order_id": 8, "email": "anacarol.ferreira@coldmail.com"}).json()["verified"]
        response = client.post("/api/chat", json={"message": "Where is order 8?"})
        assert response.json()["results"][0]["status"] == "found"
        assert client.delete("/api/session").status_code == 200
        assert client.get("/api/session").json() == {"history": [], "verified": False}
        assert client.get("/api/health").json()["counts"]["products"] == 65


def test_api_rejects_forged_scope_cross_origin_and_large_body(settings):
    with TestClient(create_app(settings)) as client:
        assert client.post("/api/chat", json={"message": "order 1", "customer_id": 3}).status_code == 422
        assert client.post("/api/chat", headers={"Origin": "https://evil.example"}, json={"message": "hi"}).status_code == 403
        assert client.post("/api/chat", json={"message": "x" * 17000}).status_code == 413
        assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400


def test_verification_rate_limit(settings):
    with TestClient(create_app(settings)) as client:
        for _ in range(5):
            response = client.post("/api/verify", json={"order_id": 999, "email": "wrong@example.com"})
            assert response.status_code == 200 and not response.json()["verified"]
        assert client.post("/api/verify", json={"order_id": 8, "email": "wrong@example.com"}).status_code == 429


def test_public_endpoints_and_assets(settings):
    with TestClient(create_app(settings)) as client:
        for path in ("/", "/static/app.js", "/static/style.css", "/static/mark.svg", "/manual", "/api/policies", "/openapi.json"):
            assert client.get(path).status_code == 200
        result = client.get("/api/catalog?category_id=5&query=Takamine").json()
        assert result["products"] and all(p["category_id"] == 5 for p in result["products"])
