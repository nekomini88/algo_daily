#!/usr/bin/env python3
import configparser
import json
import subprocess
import sys
import tempfile
import os
import urllib.error
import urllib.parse
import urllib.request
import time
from pathlib import Path

BASE = Path("/root/algo_daily")
PLAN = BASE / "algo_plan.json"
STATE = BASE / "algo_state.json"
CFG = BASE / "config.ini"

with open(PLAN, encoding="utf-8") as f:
    data = json.load(f)

try:
    with open(STATE, encoding="utf-8") as f:
        state = json.load(f)
except Exception:
    state = {"current_day": 1}

cfg = configparser.ConfigParser()
cfg.read(CFG, encoding="utf-8")
TG_CHAT_ID = cfg.get("telegram", "tg_chat_id", fallback="")
ORIGIN_CHAT_ID = cfg.get("telegram", "origin_chat_id", fallback="")
BOT_TOKEN = cfg.get("telegram", "bot_token", fallback="")

cmd = sys.argv[1] if len(sys.argv) > 1 else ""

if cmd in {"approve", "reject"}:
    if cmd == "approve":
        state["current_day"] = min(state["current_day"] + 1, len(data["plans"]))
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
        print("✅ 已进入下一章")
    else:
        print("➡️ 保持当前进度")
    raise SystemExit(0)

day = state["current_day"]
item = data["plans"][day - 1]
msg_text = f"""📚 <b>算法学习提醒 | Day {day} | 第{item["week"]}周</b>

📖 <b>今日主题：</b>{item["title"]}
🏷️ <b>分类：</b>{item["category"]}
⏱️ <b>建议时长：</b>{item["duration"]}
🧩 <b>LeetCode：</b>{item["leetcode"]}

📌 <b>学习流程：</b>
1️⃣ 看视频（30-40min）：B站看对应视频，理解思路
2️⃣ 手写代码（30-40min）：不看视频自己实现一遍
3️⃣ LeetCode刷题（20-30min）：完成对应题目

💪 <b>加油！坚持就是胜利！</b>

B站合集：https://space.bilibili.com/525438321/channel/collectiondetail?sid=180037"""

print(msg_text)

inline_markup = {
    "reply_markup": json.dumps({
        "inline_keyboard": [
            [
                {"text": "✅ 进入下一章", "callback_data": "algo_approve"},
                {"text": "➡️ 保持当前进度", "callback_data": "algo_reject"},
            ]
        ]
    })
}


def tg_request(method: str, payload: dict):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"TG API {method} failed: {e.code} {body}")


def send_text(chat_id: str, text: str, reply_markup: dict | None = None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload.update(reply_markup)
    return tg_request("sendMessage", payload)


def answer_callback(callback_query_id: str, text: str, show_alert: bool = False):
    return tg_request("answerCallbackQuery", {"callback_query_id": callback_query_id, "text": text, "show_alert": show_alert})


def edit_reply_markup(chat_id: str, message_id: int):
    payload = {"chat_id": chat_id, "message_id": message_id, "reply_markup": {}}
    try:
        tg_request("editMessageReplyMarkup", payload)
    except Exception:
        pass


def poll_callbacks():
    if not BOT_TOKEN:
        return
    offset = 0
    while True:
        try:
            updates = tg_request("getUpdates", {"offset": offset, "timeout": 15}).get("result", [])
        except Exception:
            time.sleep(1)
            continue
        if not updates:
            continue
        for u in updates:
            offset = u["update_id"] + 1
            cq = u.get("callback_query")
            if not cq:
                continue
            cq_data = cq.get("data", "")
            cq_id = cq.get("id", "")
            chat = cq.get("message", {}).get("chat", {})
            cid = str(chat.get("id", ""))
            mid = cq.get("message", {}).get("message_id")

            if cid not in {str(ORIGIN_CHAT_ID), str(TG_CHAT_ID)}:
                answer_callback(cq_id, "不在允许频道内")
                continue
            if cq_data not in {"algo_approve", "algo_reject"}:
                answer_callback(cq_id, "不支持的指令")
                continue

            before = state.get("current_day", 1)
            if cq_data == "algo_approve":
                state["current_day"] = min(state["current_day"] + 1, len(data["plans"]))
            note = "✅ 已进入下一章" if state["current_day"] != before else "➡️ 保持当前进度"
            with open(STATE, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False)

            if mid and cid:
                edit_reply_markup(cid, mid)
            answer_callback(cq_id, note, show_alert=True)
            send_text(cid, note)


try:
    if BOT_TOKEN and (ORIGIN_CHAT_ID or TG_CHAT_ID):
        send_text(ORIGIN_CHAT_ID, msg_text, inline_markup if ORIGIN_CHAT_ID else None)
        if TG_CHAT_ID and TG_CHAT_ID != ORIGIN_CHAT_ID:
            send_text(TG_CHAT_ID, msg_text)
except Exception as e:
    print(f"❌ 发送失败: {e}", file=sys.stderr)

poll_callbacks()
