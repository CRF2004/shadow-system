"""
Shadow CLI - Shop System
货币体系: 金币、宝石
商品分类: 消耗品、装备、外观、功能
"""

import json
from datetime import date, datetime
from pathlib import Path

import config
from engine import add_exp
from state import load_player, save_player


# ── Shop Items ──────────────────────────────────────────────────────────

SHOP_ITEMS = {
    # Consumables
    "hp_potion": {
        "id": "hp_potion",
        "name": "体力药水",
        "category": "consumable",
        "description": "恢复 50 HP",
        "price": 50,
        "price_type": "gold",
        "effect": {"hp": 50},
        "level_requirement": 1,
    },
    "mp_potion": {
        "id": "mp_potion",
        "name": "魔法药水",
        "category": "consumable",
        "description": "恢复 50 MP",
        "price": 50,
        "price_type": "gold",
        "effect": {"mp": 50},
        "level_requirement": 1,
    },
    "full_restore": {
        "id": "full_restore",
        "name": "全恢复药水",
        "category": "consumable",
        "description": "恢复所有 HP 和 MP",
        "price": 200,
        "price_type": "gold",
        "effect": {"hp": 100, "mp": 100},
        "level_requirement": 5,
    },
    "exp_book": {
        "id": "exp_book",
        "name": "经验之书",
        "category": "consumable",
        "description": "获得 500 EXP",
        "price": 150,
        "price_type": "gold",
        "effect": {"exp": 500},
        "level_requirement": 5,
    },
    "double_exp_ticket": {
        "id": "double_exp_ticket",
        "name": "双倍经验卡",
        "category": "consumable",
        "description": "下一次经验获得翻倍 (持续 1 次记录)",
        "price": 100,
        "price_type": "gold",
        "effect": {"double_exp": 1},
        "level_requirement": 10,
    },
    # Equipment
    "sword_of_coding": {
        "id": "sword_of_coding",
        "name": "编码之剑",
        "category": "equipment",
        "description": "STR +5",
        "price": 500,
        "price_type": "gold",
        "effect": {"stat": {"strength": 5}},
        "level_requirement": 10,
    },
    "boots_of_agility": {
        "id": "boots_of_agility",
        "name": "敏捷之靴",
        "category": "equipment",
        "description": "AGI +5",
        "price": 500,
        "price_type": "gold",
        "effect": {"stat": {"agility": 5}},
        "level_requirement": 10,
    },
    "lens_of_sight": {
        "id": "lens_of_sight",
        "name": "洞察之镜",
        "category": "equipment",
        "description": "SEN +5",
        "price": 500,
        "price_type": "gold",
        "effect": {"stat": {"sense": 5}},
        "level_requirement": 15,
    },
    "armor_endurance": {
        "id": "armor_endurance",
        "name": "耐力铠甲",
        "category": "equipment",
        "description": "VIT +5",
        "price": 500,
        "price_type": "gold",
        "effect": {"stat": {"vitality": 5}},
        "level_requirement": 15,
    },
    "crown_of_wisdom": {
        "id": "crown_of_wisdom",
        "name": "智慧王冠",
        "category": "equipment",
        "description": "INT +5",
        "price": 800,
        "price_type": "gold",
        "effect": {"stat": {"intelligence": 5}},
        "level_requirement": 20,
    },
    # Appearance
    "title_dungeon_master": {
        "id": "title_dungeon_master",
        "name": "副本大师",
        "category": "appearance",
        "description": "称号装饰: 副本大师",
        "price": 300,
        "price_type": "gold",
        "effect": {"title_suffix": "【副本大师】"},
        "level_requirement": 20,
    },
    # Functional
    "extra_daily": {
        "id": "extra_daily",
        "name": "额外副本次数",
        "category": "functional",
        "description": "增加 1 次每日副本次数",
        "price": 150,
        "price_type": "gold",
        "effect": {"extra_dungeon": 1},
        "level_requirement": 5,
    },
}


def get_shop_items(player: dict, category: str | None = None) -> list[dict]:
    """Get shop items available to the player, filtered by category if given."""
    level = player["level"]
    items = []
    for item in SHOP_ITEMS.values():
        if level >= item["level_requirement"]:
            if category is None or item["category"] == category:
                items.append(item)
    return items


def buy_item(player: dict, item_id: str) -> dict:
    """Buy an item from the shop.

    Returns:
        dict with success flag and message.
    """
    item = SHOP_ITEMS.get(item_id)
    if not item:
        return {"success": False, "message": f"❌ 未知商品: {item_id}"}

    if player["level"] < item["level_requirement"]:
        return {
            "success": False,
            "message": f"❌ 等级不足 (需要 LV.{item['level_requirement']})",
        }

    price = item["price"]
    price_type = item["price_type"]

    if price_type == "gold":
        if player.get("gold", 0) < price:
            return {
                "success": False,
                "message": f"❌ 金币不足 (需要 {price}, 当前 {player.get('gold', 0)})",
            }
        player["gold"] -= price
    elif price_type == "gem":
        if player.get("gems", 0) < price:
            return {
                "success": False,
                "message": f"❌ 宝石不足 (需要 {price}, 当前 {player.get('gems', 0)})",
            }
        player["gems"] -= price

    # Apply effect
    effect = item["effect"]
    applied = []

    if "hp" in effect:
        player["hp"] = min(100, player.get("hp", 100) + effect["hp"])
        applied.append(f"HP +{effect['hp']}")

    if "mp" in effect:
        player["mp"] = min(100, player.get("mp", 100) + effect["mp"])
        applied.append(f"MP +{effect['mp']}")

    if "exp" in effect:
        add_exp(player, effect["exp"])
        applied.append(f"EXP +{effect['exp']}")

    if "stat" in effect:
        for stat_key, stat_val in effect["stat"].items():
            player["stats"][stat_key] = player.get("stats", {}).get(stat_key, 10) + stat_val
            full_name = config.STAT_FULL_NAMES.get(stat_key, stat_key)
            cn_name = {v: k for k, v in config.STAT_NAMES_CN.items()}.get(stat_key, stat_key)
            applied.append(f"{cn_name} +{stat_val}")

    if "double_exp" in effect:
        player["doubleExpNext"] = effect["double_exp"]
        applied.append("下一次记录 EXP 翻倍")

    if "extra_dungeon" in effect:
        player["extraDungeonToday"] = player.get("extraDungeonToday", 0) + effect["extra_dungeon"]
        applied.append("额外副本次数 +1")

    if "title_suffix" in effect:
        suffixes = player.get("titleSuffixes", [])
        if effect["title_suffix"] not in suffixes:
            suffixes.append(effect["title_suffix"])
        player["titleSuffixes"] = suffixes
        applied.append(f"称号: {effect['title_suffix']}")

    # Track inventory
    player.setdefault("inventory", []).append({
        "item_id": item_id,
        "name": item["name"],
        "purchased_at": datetime.now().isoformat(),
    })

    return {
        "success": True,
        "message": f"✅ 购买: {item['name']}\n效果: {', '.join(applied)}\n消耗: {price} {price_type}",
    }


def sell_item(player: dict, item_id: str) -> dict:
    """Sell an item from inventory (50% refund)."""
    inventory = player.get("inventory", [])
    found_idx = None
    found_item = None

    for i, inv_item in enumerate(inventory):
        if inv_item["item_id"] == item_id:
            found_idx = i
            found_item = inv_item
            break

    if not found_item:
        return {"success": False, "message": f"❌ 物品不存在: {item_id}"}

    original = SHOP_ITEMS.get(item_id)
    if original:
        refund = original["price"] // 2
    else:
        refund = 10  # Default refund

    player["gold"] = player.get("gold", 0) + refund
    inventory.pop(found_idx)
    player["inventory"] = inventory

    return {
        "success": True,
        "message": f"✅ 出售: {found_item['name']}\n获得: {refund} 金币",
    }


def get_inventory(player: dict) -> list[dict]:
    """Get player inventory."""
    return player.get("inventory", [])
