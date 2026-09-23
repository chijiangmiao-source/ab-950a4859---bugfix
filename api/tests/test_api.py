"""API 端到端测试（TestClient）。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_solve_ok():
    payload = {
        "points": ["r", "a", "b", "c", "d"],
        "root": "r",
        "channels": [
            {"id": "e1", "from": "r", "to": "a", "cost": 5},
            {"id": "e2", "from": "a", "to": "b", "cost": 1},
            {"id": "e3", "from": "b", "to": "a", "cost": 1},
            {"id": "e4", "from": "b", "to": "c", "cost": 1},
            {"id": "e5", "from": "c", "to": "a", "cost": 1},
            {"id": "e6", "from": "c", "to": "d", "cost": 1},
        ],
    }
    r = client.post("/api/solve", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["total_cost"] == 8
    assert body["canonical_ids"] == ["e1", "e2", "e4", "e6"]
    assert len(body["tree"]) == 4
    assert body["record"]["contractions"] == 2
    assert len(body["record"]["expansions"]) == 2


def test_solve_three_entry_cycle_canonical():
    """三入口零代价环：规范树须为 [e0, e2, e5]，展开以 e0 进入 a 替换 e3。"""
    channels = [
        {"id": "e5", "from": "a", "to": "b", "cost": 0},
        {"id": "e2", "from": "b", "to": "c", "cost": 0},
        {"id": "e3", "from": "c", "to": "a", "cost": 0},
        {"id": "e0", "from": "r", "to": "a", "cost": 1},
        {"id": "e1", "from": "r", "to": "b", "cost": 1},
        {"id": "e4", "from": "r", "to": "c", "cost": 1},
    ]
    payload = {"points": ["r", "a", "b", "c"], "root": "r", "channels": channels}
    last = None
    # 不同的通道录入顺序须得到完全一致的响应
    for order in (channels, list(reversed(channels)), [channels[i] for i in (3, 0, 5, 1, 4, 2)]):
        r = client.post("/api/solve", json={**payload, "channels": order})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["total_cost"] == 1
        assert body["canonical_ids"] == ["e0", "e2", "e5"]
        assert [e["id"] for e in body["tree"]] == ["e0", "e2", "e5"]
        assert body["record"]["contractions"] == 1
        exps = body["record"]["expansions"]
        assert len(exps) == 1
        assert exps[0]["entering_channel"] == "e0"
        assert exps[0]["enters_node"] == "a"
        assert exps[0]["removed_cycle_channel"] == "e3"
        assert sorted(exps[0]["kept_cycle_channels"]) == ["e2", "e5"]
        if last is not None:
            assert body == last
        last = body


def test_solve_unsolvable():
    payload = {
        "points": ["r", "a", "z"],
        "root": "r",
        "channels": [{"id": "u1", "from": "r", "to": "a", "cost": 1}],
    }
    r = client.post("/api/solve", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "unsolvable"
    assert body["unreachable"] == ["z"]
    assert body["reason"]


def test_invalid_self_loop():
    payload = {
        "points": ["r", "a"],
        "root": "r",
        "channels": [{"id": "c1", "from": "a", "to": "a", "cost": 1}],
    }
    r = client.post("/api/solve", json=payload)
    assert r.status_code == 422
    body = r.json()
    assert body["status"] == "invalid"
    assert any("自环" in e for e in body["errors"])


def test_invalid_schema():
    r = client.post("/api/solve", json={"points": ["r"], "root": "r"})
    assert r.status_code == 422
    assert r.json()["status"] == "invalid"


def test_negative_cost_rejected():
    payload = {
        "points": ["r", "a"],
        "root": "r",
        "channels": [{"id": "c1", "from": "r", "to": "a", "cost": -2}],
    }
    r = client.post("/api/solve", json=payload)
    assert r.status_code == 422
    assert r.json()["status"] == "invalid"
