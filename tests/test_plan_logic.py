# -*- coding: utf-8 -*-
"""algo_daily 纯逻辑测试：计划生成 / 周次轮换 / 难度分级 / 消息生成"""
import contextlib
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN_PATH = os.path.join(BASE, "algo_plan.json")
STATE_PATH = os.path.join(BASE, "algo_state.json")

DURATION_RE = re.compile(r"^\d+(?:\.\d+)?h$")

CORE_CATEGORIES = {"数组", "链表", "哈希表", "字符串", "栈与队列",
                   "二叉树", "回溯算法", "贪心算法", "动态规划"}


def load_plan():
    with open(PLAN_PATH, encoding="utf-8") as f:
        return json.load(f)["plans"]


def difficulty_of(duration: str) -> str:
    """难度分级：按建议时长映射 → 1h=入门 / 1.5h=基础 / 2h=进阶"""
    if not DURATION_RE.match(duration):
        return "未知"
    hours = float(duration[:-1])
    if hours <= 1:
        return "入门"
    if hours <= 1.5:
        return "基础"
    return "进阶"


class TestPlanLookup:
    """计划生成：day → 计划项 的查找与完整性"""

    def test_lookup_by_index(self):
        """plans[day-1] 恰好是第 day 天的计划（algo_reminder 的取数方式）"""
        for i, item in enumerate(load_plan(), start=1):
            assert item["day"] == i

    def test_state_day_points_to_existing_plan(self):
        with open(STATE_PATH, encoding="utf-8") as f:
            state = json.load(f)
        plan = load_plan()
        day = state["current_day"]
        item = plan[day - 1]
        assert item["day"] == day

    def test_all_fields_non_empty(self):
        """消息生成所需字段（day/week/title/leetcode/duration/category）全部非空"""
        for item in load_plan():
            for key in ("day", "week", "title", "leetcode", "duration", "category"):
                assert item[key] != "", f"day {item['day']} 缺少字段: {key}"


class TestWeekRotation:
    """周次轮换：week 与 day 严格对应，每周结尾是复习日"""

    def test_week_matches_day(self):
        """week = (day-1)//7 + 1，与计划内 week 字段一致"""
        for item in load_plan():
            assert item["week"] == (item["day"] - 1) // 7 + 1

    def test_plan_spans_eight_weeks(self):
        weeks = [item["week"] for item in load_plan()]
        assert weeks == sorted(weeks)
        assert set(weeks) == set(range(1, 9))

    def test_week_boundary_is_review_day(self):
        """每个第 7 天（含最后总复习）标题都应含“复习”"""
        for item in load_plan():
            if item["day"] % 7 == 0:
                assert "复习" in item["title"], \
                    f"day {item['day']} 应是复习日: {item['title']}"


class TestDifficultyGrading:
    """难度分级：时长格式合法且可分级，覆盖全部等级"""

    def test_all_durations_parse(self):
        for item in load_plan():
            assert DURATION_RE.match(item["duration"]), \
                f"非法时长格式: {item['duration']}"

    def test_all_entries_classified(self):
        for item in load_plan():
            assert difficulty_of(item["duration"]) in {"入门", "基础", "进阶"}

    def test_distribution_covers_all_levels(self):
        levels = {difficulty_of(item["duration"]) for item in load_plan()}
        assert levels == {"入门", "基础", "进阶"}

    def test_first_day_is_basic(self):
        assert difficulty_of(load_plan()[0]["duration"]) == "基础"

    def test_final_review_is_advanced(self):
        assert difficulty_of(load_plan()[-1]["duration"]) == "进阶"


class TestCurriculumCoverage:
    """计划完整性：核心知识分类全覆盖，无重复天"""

    def test_core_categories_covered(self):
        categories = {item["category"] for item in load_plan()}
        assert CORE_CATEGORIES <= categories

    def test_no_duplicate_days(self):
        days = [item["day"] for item in load_plan()]
        assert len(days) == len(set(days))


class TestReminderMessage:
    """提醒消息生成（导入真实模块；config 无 token 时不联网）"""

    @staticmethod
    def _module():
        with contextlib.redirect_stdout(io.StringIO()):  # 抑制模块级 print
            import algo_reminder
        return algo_reminder

    def test_message_contains_today_plan(self):
        m = self._module()
        day = m.state["current_day"]
        item = m.data["plans"][day - 1]
        assert f"Day {day}" in m.msg_text
        assert item["title"] in m.msg_text
        assert item["category"] in m.msg_text
        assert item["duration"] in m.msg_text
        assert item["leetcode"] in m.msg_text
        assert "学习流程" in m.msg_text  # 固定学习流程段落

    def test_inline_keyboard_buttons(self):
        m = self._module()
        markup = json.loads(m.inline_markup["reply_markup"])
        datas = [b["callback_data"] for b in markup["inline_keyboard"][0]]
        assert datas == ["algo_approve", "algo_reject"]
