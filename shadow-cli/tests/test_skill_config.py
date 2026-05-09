"""Tests for skill_config module."""

from skill_config import (
    BUILTIN_TEMPLATES,
    get_all_templates,
    get_template,
    get_categories,
    match_by_keywords,
    match_fuzzy,
    generate_config,
    generate_skill_configs,
    get_presets,
    generate_skill_daily_tasks,
    generate_skill_emergency_task,
    get_exp_for_skill,
    save_user_template,
    load_user_templates,
    _get_templates_file,
)
from state import create_default_player


class TestBuiltinTemplates:
    def test_templates_exist(self):
        assert len(BUILTIN_TEMPLATES) >= 5

    def test_template_structure(self):
        t = BUILTIN_TEMPLATES[0]
        required = ["id", "name", "category", "unit", "icon", "exp_formula", "exp_per_unit", "daily_cap", "daily_target"]
        for key in required:
            assert key in t

    def test_common_templates_exist(self):
        ids = [t["id"] for t in BUILTIN_TEMPLATES]
        assert "vocabulary" in ids
        assert "coding" in ids
        assert "exercise" in ids
        assert "reading" in ids
        assert "commit" in ids


class TestTemplateLookup:
    def test_get_template_by_id(self):
        t = get_template("vocabulary")
        assert t is not None
        assert t["name"] == "背单词"

    def test_get_template_not_found(self):
        t = get_template("nonexistent")
        assert t is None

    def test_get_all_templates_includes_builtin(self):
        all_t = get_all_templates()
        ids = [t["id"] for t in all_t]
        assert "vocabulary" in ids

    def test_get_categories(self):
        cats = get_categories()
        assert len(cats) >= 5
        cat_ids = [c["id"] for c in cats]
        assert "学习" in cat_ids
        assert "健康" in cat_ids


class TestKeywordMatching:
    def test_match_vocabulary(self):
        t = match_by_keywords("背单词")
        assert t is not None
        assert t["id"] == "vocabulary"

    def test_match_coding(self):
        t = match_by_keywords("写代码")
        assert t is not None
        assert t["id"] == "coding"

    def test_match_exercise(self):
        t = match_by_keywords("运动健身")
        assert t is not None
        assert t["id"] == "exercise"

    def test_match_english(self):
        t = match_by_keywords("学英语")
        assert t is not None
        assert t["id"] == "vocabulary"

    def test_no_match(self):
        t = match_by_keywords("随机字符串xyz123")
        assert t is None

    def test_fuzzy_match(self):
        t = match_fuzzy("我想去跑步")
        assert t is not None
        assert t["id"] == "running"


class TestGenerateConfig:
    def test_generate_from_known_keyword(self):
        cfg = generate_config("背单词")
        assert cfg["id"] == "vocabulary"
        assert cfg["unit"] == "个"

    def test_generate_from_custom_description(self):
        cfg = generate_config("弹钢琴")
        assert cfg["id"] is not None
        assert cfg["name"] is not None
        assert cfg["exp_formula"] == "linear"

    def test_generate_generic_fallback(self):
        cfg = generate_config("一个完全不相关的描述xyz")
        assert cfg["category"] == "其他"
        assert cfg["exp_formula"] == "linear"

    def test_generate_id_lowercased(self):
        cfg = generate_config("背英语单词")
        assert cfg["id"] == cfg["id"].lower()


class TestGenerateSkillConfigs:
    def test_multiple_descriptions(self):
        configs = generate_skill_configs(["背单词", "写代码", "跑步"])
        assert len(configs) == 3
        ids = [c["id"] for c in configs]
        assert len(ids) == len(set(ids))  # All unique

    def test_empty_description_skipped(self):
        configs = generate_skill_configs(["背单词", "", "  "])
        assert len(configs) == 1

    def test_duplicate_ids_handled(self):
        # Two similar descriptions might generate same base ID
        configs = generate_skill_configs(["背单词", "背单词"])
        assert len(configs) == 2
        assert configs[0]["id"] != configs[1]["id"]


class TestPresets:
    def test_presets_exist(self):
        presets = get_presets()
        assert len(presets) >= 3

    def test_preset_structure(self):
        p = get_presets()[0]
        assert "id" in p
        assert "name" in p
        assert "skills" in p
        assert len(p["skills"]) >= 1


class TestSkillDailyTasks:
    def test_generate_from_skills(self):
        player = create_default_player()
        player["skillConfig"] = {
            "skills": [
                {"id": "coding", "name": "写代码", "exp_per_unit": 0.1, "daily_target": 100, "daily_cap": 200},
                {"id": "vocabulary", "name": "背单词", "exp_per_unit": 1, "daily_target": 50, "daily_cap": 150},
            ],
        }
        tasks = generate_skill_daily_tasks(player)
        assert len(tasks) == 2
        assert tasks[0]["type"] == "coding"
        assert tasks[1]["type"] == "vocabulary"

    def test_empty_skills(self):
        player = create_default_player()
        tasks = generate_skill_daily_tasks(player)
        assert tasks == []

    def test_emergency_task(self):
        player = create_default_player()
        player["skillConfig"] = {
            "skills": [
                {"id": "coding", "name": "写代码", "exp_per_unit": 0.1, "daily_target": 100, "daily_cap": 200},
            ],
        }
        emergency = generate_skill_emergency_task(player)
        assert emergency is not None
        assert emergency["type"] == "coding"
        assert "⚡" in emergency["name"]


class TestExpForSkill:
    def test_linear_calc(self):
        skill = {"exp_formula": "linear", "exp_per_unit": 2, "daily_cap": 100}
        exp = get_exp_for_skill(skill, 30)
        assert exp == 60

    def test_daily_cap(self):
        skill = {"exp_formula": "linear", "exp_per_unit": 5, "daily_cap": 50}
        exp = get_exp_for_skill(skill, 20)
        assert exp == 50  # Capped

    def test_zero_quantity(self):
        skill = {"exp_formula": "linear", "exp_per_unit": 5, "daily_cap": 100}
        exp = get_exp_for_skill(skill, 0)
        assert exp == 0


class TestUserTemplates:
    def test_save_and_load(self, tmp_path, monkeypatch):
        # Redirect templates file to temp location
        tf = tmp_path / "skill_templates.json"
        monkeypatch.setattr("skill_config._get_templates_file", lambda: tf)

        save_user_template({"id": "test_skill", "name": "测试技能", "category": "测试"})
        templates = load_user_templates()
        assert len(templates) == 1
        assert templates[0]["id"] == "test_skill"

    def test_duplicate_not_saved(self, tmp_path, monkeypatch):
        tf = tmp_path / "skill_templates.json"
        monkeypatch.setattr("skill_config._get_templates_file", lambda: tf)

        save_user_template({"id": "test_skill", "name": "测试技能"})
        save_user_template({"id": "test_skill", "name": "测试技能"})
        templates = load_user_templates()
        assert len(templates) == 1
