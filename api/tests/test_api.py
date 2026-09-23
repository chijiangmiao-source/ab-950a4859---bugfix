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


def test_three_entry_cycle_canonical_tiebreak():
    """环收缩参与的同优规范树：三个等代价根入口配零代价三点环。

    三棵最优树代价均为 1，规范树必须是字典序最小的 [e0,e2,e5]，
    展开以 e0 进入 a、替换环边 e3。
    """
    payload = {
        "points": ["r", "a", "b", "c"],
        "root": "r",
        "channels": [
            {"id": "e5", "from": "a", "to": "b", "cost": 0},
            {"id": "e2", "from": "b", "to": "c", "cost": 0},
            {"id": "e3", "from": "c", "to": "a", "cost": 0},
            {"id": "e0", "from": "r", "to": "a", "cost": 1},
            {"id": "e1", "from": "r", "to": "b", "cost": 1},
            {"id": "e4", "from": "r", "to": "c", "cost": 1},
        ],
    }
    r = client.post("/api/solve", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["total_cost"] == 1
    assert body["canonical_ids"] == ["e0", "e2", "e5"]
    assert sorted(e["id"] for e in body["tree"]) == ["e0", "e2", "e5"]
    assert sum(e["cost"] for e in body["tree"]) == 1
    record = body["record"]
    assert record["contractions"] == 1
    assert len(record["expansions"]) == 1
    exp = record["expansions"][0]
    assert exp["entering_channel"] == "e0"
    assert exp["enters_node"] == "a"
    assert exp["removed_cycle_channel"] == "e3"
    assert sorted(exp["kept_cycle_channels"]) == ["e2", "e5"]


def test_three_entry_cycle_shuffled_input_order():
    """调整通道录入顺序后，API 仍返回同一规范树。"""
    payload = {
        "points": ["r", "c", "a", "b"],
        "root": "r",
        "channels": [
            {"id": "e4", "from": "r", "to": "c", "cost": 1},
            {"id": "e0", "from": "r", "to": "a", "cost": 1},
            {"id": "e3", "from": "c", "to": "a", "cost": 0},
            {"id": "e1", "from": "r", "to": "b", "cost": 1},
            {"id": "e5", "from": "a", "to": "b", "cost": 0},
            {"id": "e2", "from": "b", "to": "c", "cost": 0},
        ],
    }
    r = client.post("/api/solve", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["total_cost"] == 1
    assert body["canonical_ids"] == ["e0", "e2", "e5"]
    assert body["record"]["contractions"] == 1
    assert body["record"]["expansions"][0]["entering_channel"] == "e0"
    assert body["record"]["expansions"][0]["removed_cycle_channel"] == "e3"


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
