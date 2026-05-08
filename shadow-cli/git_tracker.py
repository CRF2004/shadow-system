"""
Shadow CLI - Git Tracker
Reads git logs to auto-track commits and grant EXP.
"""

import json
import os
import subprocess
from datetime import date, datetime
from pathlib import Path

import config
from engine import add_exp, check_achievements, get_exp_for_action
from state import load_player, save_player


def get_git_root(path: str = ".") -> str | None:
    """Get the git root directory, or None if not in a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5, cwd=path
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def get_daily_commits(git_root: str = ".", since_date: str | None = None) -> list[dict]:
    """Get commits since a given date (default: today).

    Returns list of dicts with: hash, author, date, message, files_changed, insertions, deletions
    """
    since = since_date or date.today().isoformat()
    format_str = "%H|%an|%ae|%ai|%s"

    try:
        result = subprocess.run(
            ["git", "log", f"--since={since}", f"--format={format_str}", "--numstat"],
            capture_output=True, text=True, timeout=10, cwd=git_root
        )
        if result.returncode != 0:
            return []

        commits = []
        lines = result.stdout.strip().split("\n")
        i = 0

        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            # Parse commit header
            parts = line.split("|")
            if len(parts) < 5:
                i += 1
                continue

            commit = {
                "hash": parts[0][:8],
                "author": parts[1],
                "email": parts[2],
                "date": parts[3],
                "message": parts[4],
                "files": [],
                "insertions": 0,
                "deletions": 0,
            }

            i += 1
            # Parse numstat lines until next commit or end
            while i < len(lines):
                stat_line = lines[i].strip()
                if not stat_line or "|" in stat_line:
                    break
                stat_parts = stat_line.split()
                if len(stat_parts) >= 3:
                    ins = int(stat_parts[0]) if stat_parts[0] != "-" else 0
                    dels = int(stat_parts[1]) if stat_parts[1] != "-" else 0
                    commit["files"].append({
                        "path": stat_parts[2],
                        "insertions": ins,
                        "deletions": dels,
                    })
                    commit["insertions"] += ins
                    commit["deletions"] += dels
                i += 1

            commits.append(commit)

        return commits

    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def get_all_time_commits(git_root: str = ".") -> dict:
    """Get commit statistics: total, daily breakdown."""
    try:
        result = subprocess.run(
            ["git", "log", "--format=%ai", "--numstat"],
            capture_output=True, text=True, timeout=30, cwd=git_root
        )
        if result.returncode != 0:
            return {"total": 0, "daily": {}}

        daily = {}
        current_date = None
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # Date line: 2026-05-08 14:30:00 +0800
            if len(line) >= 10 and line[4] == "-" and line[7] == "-":
                current_date = line[:10]
                if current_date not in daily:
                    daily[current_date] = {"commits": 0, "insertions": 0, "deletions": 0}
                daily[current_date]["commits"] += 1
            elif current_date and "\t" in line:
                parts = line.split()
                if len(parts) >= 3:
                    ins = int(parts[0]) if parts[0] != "-" else 0
                    dels = int(parts[1]) if parts[1] != "-" else 0
                    daily[current_date]["insertions"] += ins
                    daily[current_date]["deletions"] += dels

        return {"total": sum(d["commits"] for d in daily.values()), "daily": daily}

    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {"total": 0, "daily": {}}


def scan_commits_and_grant(player: dict, git_root: str = ".", since_date: str | None = None) -> dict:
    """Scan git commits since date and grant EXP.

    Returns:
        dict with commits_found, exp_granted, levelup_msgs, achievement_msgs
    """
    commits = get_daily_commits(git_root, since_date)
    commit_count = len(commits)

    if commit_count == 0:
        return {
            "commits_found": 0,
            "exp_granted": 0,
            "levelup_msgs": [],
            "achievement_msgs": [],
            "message": "没有找到新的 commit",
        }

    streak = player.get("streak", 0)
    combo = player.get("combo", 0)
    exp = get_exp_for_action("commit", commit_count, streak, combo)

    levelup_msgs = add_exp(player, exp)
    player["commitCount"] = player.get("commitCount", 0) + commit_count

    # Check achievements
    new_achievements = check_achievements(player)
    ach_msgs = []
    for ach in new_achievements:
        ach_msgs.append(f"🏆 成就解锁: {ach['name']} (+{ach['reward_exp']} EXP)")

    save_player(player)

    # Log the scan
    log_file = config.LOGS_DIR / f"git_scan_{date.today().isoformat()}.json"
    scan_log = {
        "timestamp": datetime.now().isoformat(),
        "commits_found": commit_count,
        "exp_granted": exp,
        "commit_hashes": [c["hash"] for c in commits],
    }
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(scan_log, f, indent=2, ensure_ascii=False)

    return {
        "commits_found": commit_count,
        "exp_granted": exp,
        "levelup_msgs": levelup_msgs,
        "achievement_msgs": ach_msgs,
        "message": f"✅ 扫描到 {commit_count} 个 commit → +{exp} EXP",
    }


def install_git_hook(git_root: str = ".") -> dict:
    """Install a post-commit hook that logs commits to shadow state."""
    hooks_dir = Path(git_root) / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_file = hooks_dir / "post-commit"

    hook_content = f"""#!/bin/sh
# Shadow System - Post-commit hook
# Auto-records commit to shadow state

HASH=$(git rev-parse HEAD 2>/dev/null | head -c8)
DATE=$(date -Iseconds 2>/dev/null || date +%Y-%m-%dT%H:%M:%S)
MESSAGE=$(git log -1 --format=%s 2>/dev/null)

SHADOW_LOG="{config.LOGS_DIR}"
mkdir -p "$SHADOW_LOG"
echo "{{\\"timestamp\\":\\"$DATE\\",\\"hash\\":\\"$HASH\\",\\"message\\":\\"$MESSAGE\\"}}" >> "$SHADOW_LOG/git_commits.log"
"""

    hook_file.write_text(hook_content, encoding="utf-8")
    os.chmod(hook_file, 0o755)

    return {
        "success": True,
        "path": str(hook_file),
        "message": f"✅ Git hook 已安装: {hook_file}",
    }


def uninstall_git_hook(git_root: str = ".") -> dict:
    """Remove the shadow post-commit hook."""
    hooks_dir = Path(git_root) / ".git" / "hooks"
    hook_file = hooks_dir / "post-commit"

    if hook_file.exists():
        content = hook_file.read_text()
        if "Shadow System" in content:
            hook_file.unlink()
            return {"success": True, "message": "✅ Git hook 已移除"}

    return {"success": False, "message": "未找到 Shadow hook"}


def get_git_status_info() -> str:
    """Get a summary of git status and recent activity."""
    git_root = get_git_root()
    if not git_root:
        return "⚠️ 不在 Git 仓库中\n使用 'shadow scan-git [路径]' 指定仓库"

    all_time = get_all_time_commits(git_root)
    today_commits = get_daily_commits(git_root)

    try:
        result = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True, text=True, timeout=5, cwd=git_root
        )
        uncommitted = result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        uncommitted = ""

    lines = [
        "┌──────────────────────────────────────────┐",
        "│  📦 Git 追踪状态                          │",
        "├──────────────────────────────────────────┤",
        f"│  仓库: {git_root[:30]}                │",
        f"│  总 commit: {all_time['total']}                         │",
        f"│  今日 commit: {len(today_commits)}                         │",
    ]

    if today_commits:
        lines.append("│                                          │")
        lines.append("│  今日提交:                                │")
        for c in today_commits[:5]:
            msg = c["message"][:25]
            lines.append(f"│    {c['hash'][:6]} {msg}    │")

    if uncommitted:
        lines.append("│                                          │")
        lines.append("│  未提交的变更:                             │")
        for stat_line in uncommitted.split("\n")[:3]:
            lines.append(f"│    {stat_line[:35]}     │")

    lines.append("├──────────────────────────────────────────┤")
    lines.append("│  使用 'shadow scan-git' 扫描并获取 EXP    │")
    lines.append("└──────────────────────────────────────────┘")

    return "\n".join(lines)
