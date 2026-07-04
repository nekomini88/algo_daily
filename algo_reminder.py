#!/usr/bin/env python3
import configparser
import json
import subprocess
import sys
import tempfile
import os
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
CHAT_ID = cfg.get("telegram", "chat_id", fallback="")

cmd = sys.argv[1] if len(sys.argv) > 1 else ""

if cmd == "approve":
    state["current_day"] = min(state["current_day"] + 1, len(data["plans"]))
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    print("✅ 已进入下一章")
    raise SystemExit(0)

day = state["current_day"]
item = data["plans"][day - 1]
msg = f"""📚 算法学习提醒 | Day {day} | 第{item["week"]}周

📖 今日主题：{item["title"]}
🏷️ 分类：{item["category"]}
⏱️ 建议时长：{item["duration"]}
🧩 LeetCode：{item["leetcode"]}

📌 学习流程：
1️⃣ 看视频（30-40min）：B站看对应视频，理解思路
2️⃣ 手写代码（30-40min）：不看视频自己实现一遍
3️⃣ LeetCode刷题（20-30min）：完成对应题目

💪 加油！坚持就是胜利！
回复 /approve 进入下一章

B站合集：https://space.bilibili.com/525438321/channel/collectiondetail?sid=180037"""

print(msg)

if CHAT_ID:
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(msg)
            tmp_path = f.name
        subprocess.run(
            ["hermes", "send", "--to", f"telegram:{CHAT_ID}", "--file", tmp_path],
            check=False
        )
        os.unlink(tmp_path)
    except Exception as e:
        print(f"❌ 发送失败: {e}", file=sys.stderr)
