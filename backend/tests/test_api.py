import pytest
from fastapi.testclient import TestClient

from conftest import needs_model


@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth(client):
    r = client.post("/api/auth/login", json={"login": "admin", "password": "admin-pass-123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_login_rejects_bad_password(client):
    assert client.post("/api/auth/login", json={"login": "admin", "password": "x"}).status_code == 401


def test_requires_auth(client):
    assert client.get("/api/objects").status_code == 401


def test_objects_and_competitors(client, auth):
    objs = client.get("/api/objects", headers=auth).json()
    ours = [o for o in objs if o["has_dashboard"]]
    assert len(objs) == 9 and len(ours) == 1
    comps = client.get(f"/api/projects/{ours[0]['id']}/competitors", headers=auth, params={"from": "3кв. 26", "to": "2кв. 27"}).json()
    assert len(comps) == 9
    intel = next(c for c in comps if c["id"] == "intel")
    assert [s["price"] for s in intel["series"]] == [545, 555, 578, 590]
    assert next(c for c in comps if c["id"] == "ahead")["enabled_default"] is False


def test_scenario_roundtrip(client, auth):
    assert client.put("/api/projects/1/scenario", headers=auth, json={"state": {"chips": {"ahead": True}}}).status_code == 200
    assert client.get("/api/projects/1/scenario", headers=auth).json() == {"chips": {"ahead": True}}


@needs_model
def test_recalc_flow(client, auth, monkeypatch):
    from app.calc import client as calc

    m = client.get("/api/projects/1/model", headers=auth).json()
    queues = {q: {"price": v["price"], "area": v["area"]} for q, v in m["queues"].items()}
    # без изменений — значения файла, воркер не нужен
    r = client.post("/api/projects/1/recalc", headers=auth, json={"model_version": m["model_version"], "queues": queues})
    assert r.json()["fr"] == m["fr"]

    seen = {}

    async def fake(version, writes, reads):
        seen["writes"] = writes
        return {"values": {"fr": 1.0, "llcr": 2.0}, "calc_ms": 5}

    monkeypatch.setattr(calc, "recalc", fake)
    i = m["labels"].index("3кв. 26")
    queues["1"]["price"][i] += 10
    r = client.post("/api/projects/1/recalc", headers=auth, json={"model_version": m["model_version"], "queues": queues})
    assert r.json() == {"fr": 1.0, "llcr": 2.0, "calc_ms": 5}
    assert [w["cell"] for w in seen["writes"]] == ["W12"]

    queues["1"]["area"][i] += 100  # итог площади нарушен
    r = client.post("/api/projects/1/recalc", headers=auth, json={"model_version": m["model_version"], "queues": queues})
    assert r.status_code == 422

    r = client.post("/api/projects/1/recalc", headers=auth, json={"model_version": "old", "queues": queues})
    assert r.status_code == 409


def test_upload_requires_admin_and_validates(client, auth):
    r = client.post("/api/projects/1/model", headers=auth, files={"file": ("x.txt", b"hello")})
    assert r.status_code == 422
    r = client.post("/api/projects/1/model", headers=auth, files={"file": ("bad.xlsx", b"not a zip")})
    assert r.status_code == 422 and "не читается" in r.json()["detail"]
