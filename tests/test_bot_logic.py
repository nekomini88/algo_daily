# -*- coding: utf-8 -*-
"""algo_bot 回调逻辑测试：日期轮换(approve/reject) / 权限过滤 / 进度持久化"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import algo_bot  # noqa: E402  模块级仅读配置/JSON，bot_token 为空时不联网

# 与 config.ini 中配置一致的可信频道
ALLOWED = {"-1003903562660", "7200170648"}


def make_update(cid="-1003903562660", data="algo_approve", cq_id="cq1", mid=42):
    """构造一个 Telegram callback_query 更新"""
    return {
        "callback_query": {
            "id": cq_id,
            "data": data,
            "message": {"message_id": mid, "chat": {"id": cid}},
        }
    }


@pytest.fixture(autouse=True)
def isolated_bot(tmp_path, monkeypatch):
    """隔离环境：临时 state 文件 + 打桩网络调用，避免污染真实进度"""
    calls = {"callback": [], "text": [], "edit": []}
    monkeypatch.setattr(algo_bot, "STATE", tmp_path / "algo_state.json")
    monkeypatch.setattr(algo_bot, "allowed_chats", set(ALLOWED))
    monkeypatch.setattr(
        algo_bot, "answer_callback",
        lambda qid, text, show_alert=False: calls["callback"].append((qid, text, show_alert)),
    )
    monkeypatch.setattr(
        algo_bot, "send_text",
        lambda cid, text: calls["text"].append((cid, text)),
    )
    monkeypatch.setattr(
        algo_bot, "edit_reply_markup",
        lambda cid, mid: calls["edit"].append((cid, mid)),
    )
    algo_bot.state = {"current_day": 1}
    return calls


def read_state_file():
    """读取被写盘的进度（验证持久化）"""
    with open(algo_bot.STATE, encoding="utf-8") as f:
        return json.load(f)


class TestApprove:
    """✅ 进入下一章：日期轮换 +1，封顶不越界"""

    def test_approve_advances_day(self, isolated_bot):
        algo_bot.process(make_update(data="algo_approve"))
        assert algo_bot.state["current_day"] == 2
        assert read_state_file()["current_day"] == 2  # 已持久化到文件
        assert isolated_bot["callback"][0][1] == "✅ 已进入下一章"
        assert isolated_bot["callback"][0][2] is True  # show_alert=True
        assert isolated_bot["text"][0][1] == "✅ 已进入下一章"

    def test_approve_clamps_at_last_day(self, isolated_bot):
        """最后一天再 approve 应封顶，不越界"""
        last = len(algo_bot.data["plans"])
        algo_bot.state["current_day"] = last
        algo_bot.process(make_update(data="algo_approve"))
        assert algo_bot.state["current_day"] == last
        # 无实际变化 → 提示保持当前进度
        assert isolated_bot["callback"][0][1] == "➡️ 保持当前进度"

    def test_approve_clears_buttons_and_answers(self, isolated_bot):
        algo_bot.process(make_update(data="algo_approve"))
        assert isolated_bot["edit"] == [("-1003903562660", 42)]  # 移除按钮
        assert isolated_bot["callback"][0][0] == "cq1"            # 回执原 callback


class TestReject:
    """➡️ 保持当前进度：day 不变"""

    def test_reject_keeps_day(self, isolated_bot):
        algo_bot.process(make_update(data="algo_reject"))
        assert algo_bot.state["current_day"] == 1
        assert read_state_file()["current_day"] == 1
        assert isolated_bot["callback"][0][1] == "➡️ 保持当前进度"


class TestPermission:
    """权限过滤：仅允许配置频道，未知指令拒绝"""

    def test_unauthorized_chat_rejected(self, isolated_bot):
        algo_bot.process(make_update(cid="999999"))
        assert algo_bot.state["current_day"] == 1
        assert isolated_bot["callback"][0][1] == "不在允许频道内"
        assert isolated_bot["text"] == []  # 不向外部频道发通知

    def test_origin_chat_allowed(self, isolated_bot):
        algo_bot.process(make_update(cid="7200170648"))
        assert algo_bot.state["current_day"] == 2

    def test_unknown_command_rejected(self, isolated_bot):
        algo_bot.process(make_update(data="bogus"))
        assert algo_bot.state["current_day"] == 1
        assert isolated_bot["callback"][0][1] == "不支持的指令"

    def test_non_callback_update_is_noop(self, isolated_bot):
        algo_bot.process({"message": {"text": "hello"}})
        assert algo_bot.state["current_day"] == 1
        assert isolated_bot["callback"] == []
        assert isolated_bot["text"] == []
