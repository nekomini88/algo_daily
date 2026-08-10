# -*- coding: utf-8 -*-
"""algo_daily 核心逻辑测试：计划读取与进度状态"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PLAN_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "algo_plan.json")
STATE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "algo_state.json")


class TestPlanLoading:
    """学习计划读取测试"""

    def test_plan_file_exists(self):
        assert os.path.exists(PLAN_PATH)

    def test_plan_is_valid_json(self):
        with open(PLAN_PATH, encoding="utf-8") as f:
            plan = json.load(f)
        assert isinstance(plan, dict)
        assert "plans" in plan
        assert len(plan["plans"]) > 0

    def test_plan_entries_have_required_fields(self):
        with open(PLAN_PATH, encoding="utf-8") as f:
            plan = json.load(f)
        first = plan["plans"][0]
        # 每项含 day/title/leetcode/duration/category
        for key in ["day", "title", "leetcode", "duration", "category"]:
            assert key in first, f"缺少字段: {key}"
        assert first["title"] != ""

    def test_plan_days_are_sequential(self):
        with open(PLAN_PATH, encoding="utf-8") as f:
            plan = json.load(f)
        days = [p["day"] for p in plan["plans"]]
        assert days == sorted(days)
        assert len(set(days)) == len(days)  # 无重复


class TestStateProgress:
    """进度状态测试"""

    def test_state_file_exists(self):
        assert os.path.exists(STATE_PATH)

    def test_state_has_current_day(self):
        with open(STATE_PATH, encoding="utf-8") as f:
            state = json.load(f)
        assert "current_day" in state
        assert isinstance(state["current_day"], int)

    def test_state_day_in_range(self):
        with open(STATE_PATH, encoding="utf-8") as f:
            state = json.load(f)
        with open(PLAN_PATH, encoding="utf-8") as f:
            plan = json.load(f)
        max_day = max(p["day"] for p in plan["plans"])
        assert 1 <= state["current_day"] <= max_day


class TestTgRequest:
    """Telegram 请求构造测试（mock urllib）"""

    def test_tg_request_url_and_payload(self, monkeypatch):
        captured = {}

        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b'{"ok": true}'

        import urllib.request

        def fake_urlopen(req, timeout=30):
            captured["url"] = req.full_url
            captured["data"] = req.data
            captured["method"] = req.method
            return FakeResp()

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        import algo_reminder
        algo_reminder.BOT_TOKEN = "TESTTOKEN"
        result = algo_reminder.tg_request("sendMessage", {"chat_id": "-100", "text": "hi"})
        assert "api.telegram.org/botTESTTOKEN/sendMessage" in captured["url"]
        assert captured["method"] == "POST"
        assert json.loads(captured["data"])["chat_id"] == "-100"
        assert result == {"ok": True}
