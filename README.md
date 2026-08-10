# 算法学习日报（algo_daily）

## 项目简介

按 `algo_plan.json` 中的逐日算法学习计划，每天通过 Telegram 推送当天的算法学习提醒（主题、配套 LeetCode 题号、预计时长、分类）。学习计划覆盖数组、链表、哈希表、字符串、栈与队列等模块的逐日刷题安排。

## 功能特性

- 基于 `algo_plan.json` 的每日计划表，按 `algo_state.json` 中的进度（`current_day`）推送当天学习内容
- Telegram 消息附带"完成/未完成"回调按钮，通过 bot 回调推进或保持进度
- `algo_reminder.py`：每日提醒入口（由 `algo_daily.sh` 调用），支持 `approve`/`reject` 手动推进/保持进度
- `algo_bot.py`：Telegram bot 轮询与回调处理（处理内联按钮点击，更新 `algo_state.json`）
- 每日学习材料目录 `files/YYYY-MM-DD/`

## 目录结构

```
algo_daily/
├── algo_daily.sh       # 一键运行脚本（调用 algo_reminder.py）
├── algo_reminder.py    # 每日提醒：读取计划+进度，发送当天学习提醒
├── algo_bot.py         # Telegram bot：轮询更新、处理 approve/reject 回调
├── algo_plan.json      # 学习计划表（day/week/title/leetcode/duration/category）
├── algo_state.json     # 当前进度（current_day）
├── config.ini          # 实际配置（Telegram bot token、chat_id）
├── config.ini.example  # 配置示例（复制为 config.ini 并填入 token）
├── files/              # 按日期存放的学习材料目录
└── cron.log            # 运行日志
```

## 运行方式

```bash
# 发送今日算法学习提醒（读取 algo_state.json 中 current_day 对应的计划）
bash algo_daily.sh
# 等价于：
python3 algo_reminder.py

# 手动推进进度到下一章 / 保持当前进度
python3 algo_reminder.py approve
python3 algo_reminder.py reject
```

定时运行：将 `algo_daily.sh` 挂到 cron 即可每日自动推送。

## 依赖/配置

- 纯 Python 标准库（urllib/json），无第三方依赖
- 配置：复制 `config.ini.example` 为 `config.ini`，填写：
  - `[telegram] bot_token`：Telegram Bot Token
  - `[telegram] tg_chat_id`：接收提醒的频道/群 ID
  - `[telegram] origin_chat_id`：消息来源 chat id（回调校验用）
- 注意：`algo_bot.py`/`algo_reminder.py` 中路径写死为 `/root/algo_daily`，移动目录需同步修改
