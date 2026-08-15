#!/usr/bin/env python3
import configparser
import json
from pathlib import Path
import urllib.error
import urllib.request

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


allowed_chats = {str(x) for x in [ORIGIN_CHAT_ID, TG_CHAT_ID] if x}


def process(update: dict):
    cq = update.get("callback_query")
    if not cq:
        return
    cq_data = cq.get("data", "")
    cq_id = cq.get("id", "")
    chat = cq.get("message", {}).get("chat", {})
    cid = str(chat.get("id", ""))
    mid = cq.get("message", {}).get("message_id")
    if cid not in allowed_chats:
        answer_callback(cq_id, "不在允许频道内")
        return
    if cq_data not in {"algo_approve", "algo_reject"}:
        answer_callback(cq_id, "不支持的指令")
        return
    before = state.get("current_day", 1)
    if cq_data == "algo_approve":
        state["current_day"] = min(state["current_day"] + 1, len(data["plansans"] if "plansans" in data else data.get("plans", [])))
    note = "✅ 已进入下一章" if state["current_day"] != before else "➡️ 保持当前进度"
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    if mid and cid:
        edit_reply_markup(cid, mid)
    answer_callback(cq_id, note, show_alert=True)
    send_text(cid, note)


if __name__ == "__main__":
    offset = 0
    while True:
        try:
            updates = tg_request("getUpdates", {"offset": offset, "timeout": 15}).get("result", [])
        except Exception:
            continue
        for u in updates:
            offset = u["update_id"] + 1
            process(u)
