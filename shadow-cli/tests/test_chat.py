"""
Phase 6 Tests - Chat Processor (OpenAI-compatible API)
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from state import create_default_player
from chat_processor import parse_message, execute_action, build_chat_response, stream_response


class TestChatParser(unittest.TestCase):
    """Test message parsing logic."""

    def test_slash_status(self):
        result = parse_message("/status")
        self.assertEqual(result["action"], "status")
        self.assertEqual(result["command"], "/status")

    def test_slash_daily(self):
        result = parse_message("/daily")
        self.assertEqual(result["action"], "daily")

    def test_slash_summon_with_type(self):
        result = parse_message("/summon explore")
        self.assertEqual(result["action"], "summon")
        self.assertEqual(result["params"]["soldier_type"], "explore")

    def test_slash_add_stat(self):
        result = parse_message("/add str 3")
        self.assertEqual(result["action"], "allocate_stat")
        self.assertEqual(result["params"]["stat"], "str")
        self.assertEqual(result["params"]["amount"], 3)

    def test_natural_vocabulary(self):
        result = parse_message("背了50个单词")
        self.assertEqual(result["action"], "record")
        self.assertEqual(result["params"]["action_type"], "vocabulary")
        self.assertEqual(result["params"]["amount"], 50)

    def test_natural_exercise(self):
        result = parse_message("运动30分钟")
        self.assertEqual(result["action"], "record")
        self.assertEqual(result["params"]["action_type"], "exercise")
        self.assertEqual(result["params"]["amount"], 30)

    def test_natural_steps(self):
        result = parse_message("走了10000步")
        self.assertEqual(result["action"], "record")
        self.assertEqual(result["params"]["action_type"], "steps")
        self.assertEqual(result["params"]["amount"], 10000)

    def test_natural_coding(self):
        result = parse_message("写了500行代码")
        self.assertEqual(result["action"], "record")
        self.assertEqual(result["params"]["action_type"], "coding_lines")
        self.assertEqual(result["params"]["amount"], 500)

    def test_natural_reading(self):
        result = parse_message("读了40页")
        self.assertEqual(result["action"], "record")
        self.assertEqual(result["params"]["action_type"], "reading_pages")
        self.assertEqual(result["params"]["amount"], 40)

    def test_fuzzy_status(self):
        result = parse_message("看看我的状态")
        self.assertEqual(result["action"], "status")

    def test_fuzzy_daily(self):
        result = parse_message("今天的任务")
        self.assertEqual(result["action"], "daily")

    def test_fuzzy_greeting(self):
        result = parse_message("你好")
        self.assertEqual(result["action"], "greeting")

    def test_fuzzy_help(self):
        result = parse_message("怎么用")
        self.assertEqual(result["action"], "help")

    def test_empty_message(self):
        result = parse_message("")
        self.assertEqual(result["action"], "unknown")

    def test_freeform(self):
        result = parse_message("今天天气不错")
        self.assertEqual(result["action"], "freeform")

    def test_chinese_slash_commands(self):
        result = parse_message("/状态")
        self.assertEqual(result["action"], "status")

        result = parse_message("/召唤 explore")
        self.assertEqual(result["action"], "summon")

        result = parse_message("/每日任务")
        self.assertEqual(result["action"], "daily")


class TestChatExecution(unittest.TestCase):
    """Test action execution and response formatting."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.state_dir = Path(self.temp_dir) / "shadow-state"
        self.state_dir.mkdir()
        os.environ["SHADOW_STATE_DIR"] = str(self.state_dir)
        self.player = create_default_player()

    def tearDown(self):
        os.environ.pop("SHADOW_STATE_DIR", None)

    def test_execute_status(self):
        result = execute_action(self.player, "status", {})
        self.assertIn("暗影君主", result["response"])
        self.assertIn("LV.1", result["response"])

    def test_execute_daily(self):
        result = execute_action(self.player, "daily", {})
        self.assertIn("今日暗影任务", result["response"])

    def test_execute_record_vocabulary(self):
        result = execute_action(self.player, "record", {"action_type": "vocabulary", "amount": 50})
        self.assertIn("+50 EXP", result["response"])

    def test_execute_record_exercise(self):
        result = execute_action(self.player, "record", {"action_type": "exercise", "amount": 30})
        self.assertIn("exercise", result["response"].lower())
        self.assertGreater(result["response"].count("EXP"), 0)

    def test_execute_greeting(self):
        result = execute_action(self.player, "greeting", {})
        self.assertIn("暗影君主", result["response"])

    def test_execute_help(self):
        result = execute_action(self.player, "help", {})
        self.assertIn("命令指南", result["response"])

    def test_execute_summon(self):
        result = execute_action(self.player, "summon", {"soldier_type": "explore"})
        self.assertTrue(result.get("success") or "不足" in result["response"])

    def test_execute_army(self):
        result = execute_action(self.player, "army", {})
        self.assertIn("暗影军团", result["response"])

    def test_execute_achievements(self):
        result = execute_action(self.player, "achievements", {})
        self.assertIn("成就列表", result["response"])

    def test_execute_shop(self):
        result = execute_action(self.player, "shop", {})
        self.assertIn("暗影商店", result["response"])

    def test_execute_inventory(self):
        result = execute_action(self.player, "inventory", {})
        self.assertIn("背包", result["response"])

    def test_execute_dungeon(self):
        result = execute_action(self.player, "dungeon", {})
        self.assertIn("副本", result["response"])

    def test_execute_allocate_stat(self):
        self.player["statPoints"] = 5
        result = execute_action(self.player, "allocate_stat", {"stat": "str", "amount": 2})
        self.assertIn("成功", result["response"])
        from state import config
        # Default strength is 10, +2 = 12
        self.assertEqual(self.player["stats"][config.STAT_FULL_NAMES["str"]], 12)

    def test_unknown_action(self):
        result = execute_action(self.player, "unknown", {})
        self.assertIn("模糊", result["response"])

    def test_freeform_action(self):
        result = execute_action(self.player, "freeform", {"text": "今天天气不错"})
        self.assertIn("暗影君主", result["response"])


class TestOpenAIFormat(unittest.TestCase):
    """Test OpenAI-compatible response format."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.state_dir = Path(self.temp_dir) / "shadow-state"
        self.state_dir.mkdir()
        os.environ["SHADOW_STATE_DIR"] = str(self.state_dir)
        self.player = create_default_player()

    def tearDown(self):
        os.environ.pop("SHADOW_STATE_DIR", None)

    def test_build_chat_response_structure(self):
        action_result = execute_action(self.player, "status", {})
        response = build_chat_response(action_result)
        self.assertEqual(response["object"], "chat.completion")
        self.assertEqual(response["choices"][0]["message"]["role"], "assistant")
        self.assertIn("content", response["choices"][0]["message"])
        self.assertEqual(response["choices"][0]["finish_reason"], "stop")
        self.assertIn("usage", response)

    def test_build_chat_response_contains_content(self):
        action_result = execute_action(self.player, "status", {})
        response = build_chat_response(action_result)
        self.assertIn("暗影君主", response["choices"][0]["message"]["content"])

    def test_stream_response_format(self):
        action_result = execute_action(self.player, "status", {})
        chunks = list(stream_response(action_result))
        self.assertTrue(len(chunks) > 2)  # At least opening, content, and closing
        self.assertTrue(chunks[0].startswith("data: "))
        self.assertTrue(chunks[-1].startswith("data: [DONE]"))

    def test_stream_response_content(self):
        action_result = execute_action(self.player, "status", {})
        full_text = ""
        for chunk in stream_response(action_result):
            if chunk.startswith("data: [DONE]"):
                break
            data = json.loads(chunk[6:])
            if data["choices"][0].get("delta", {}).get("content"):
                full_text += data["choices"][0]["delta"]["content"]
        self.assertIn("暗影君主", full_text)


if __name__ == "__main__":
    unittest.main()
