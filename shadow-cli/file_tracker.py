"""
Shadow CLI - File Tracker
Monitors code file changes to auto-track coding activity.
Uses simple directory scanning (no watchdog dependency).
"""

import json
import os
from datetime import date, datetime
from pathlib import Path
from hashlib import md5

import config
from engine import add_exp, get_exp_for_action, check_achievements
from state import load_player, save_player


# ── Tracked file extensions ────────────────────────────────────────────

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".go", ".rs", ".java", ".c", ".cpp", ".h", ".hpp",
    ".css", ".html", ".vue", ".svelte",
    ".rb", ".php", ".swift", ".kt",
    ".sh", ".bash", ".zsh",
}

# Directories to skip
SKIP_DIRS = {
    "__pycache__", ".git", ".svn", "node_modules", ".venv", "venv",
    ".tox", ".mypy_cache", ".pytest_cache", ".next", ".nuxt",
    "dist", "build", ".cache", ".idea", ".vscode",
}


def is_code_file(path: Path) -> bool:
    """Check if file is a trackable code file."""
    return path.is_file() and path.suffix in CODE_EXTENSIONS


def should_skip_dir(dir_name: str) -> bool:
    """Check if directory should be skipped."""
    return dir_name in SKIP_DIRS or dir_name.startswith(".")


def scan_directory(root: str | Path, skip_hidden: bool = True) -> list[dict]:
    """Scan a directory for code files.

    Returns list of dicts: {path, size, lines, extension, modified}
    """
    root = Path(root)
    files = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out skip dirs
        dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]

        for fname in filenames:
            fpath = Path(dirpath) / fname
            if not is_code_file(fpath):
                continue

            try:
                stat = fpath.stat()
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    line_count = content.count("\n") + 1
                    # Quick hash for change detection
                    file_hash = md5(content.encode("utf-8", errors="ignore")).hexdigest()[:12]
            except (PermissionError, OSError):
                continue

            files.append({
                "path": str(fpath),
                "size": stat.st_size,
                "lines": line_count,
                "extension": fpath.suffix,
                "modified": stat.st_mtime,
                "hash": file_hash,
            })

    return files


def get_snapshot_dir() -> Path:
    """Get the snapshot directory for file tracking data."""
    snap_dir = config.STATE_DIR / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    return snap_dir


def save_snapshot(root: str = ".", label: str | None = None) -> dict:
    """Take a snapshot of all code files in a directory.

    Returns:
        dict with file_count, total_lines, total_size, files: [{path, lines, hash}]
    """
    root = Path(root).resolve()
    files = scan_directory(root)

    total_lines = sum(f["lines"] for f in files)
    total_size = sum(f["size"] for f in files)

    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "root": str(root),
        "label": label or date.today().isoformat(),
        "file_count": len(files),
        "total_lines": total_lines,
        "total_size": total_size,
        "files": [
            {"path": f["path"], "lines": f["lines"], "hash": f["hash"]}
            for f in files
        ],
    }

    snap_dir = get_snapshot_dir()
    snap_file = snap_dir / f"snapshot_{label or date.today().isoformat()}_{int(datetime.now().timestamp())}.json"
    with open(snap_file, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    return snapshot


def compare_snapshots(root: str = ".") -> dict | None:
    """Compare current state with last snapshot.

    Returns diff or None if no previous snapshot exists.
    """
    snap_dir = get_snapshot_dir()
    snapshots = sorted(snap_dir.glob("snapshot_*.json"))

    if not snapshots:
        return None

    # Load last snapshot
    with open(snapshots[-1], "r", encoding="utf-8") as f:
        last = json.load(f)

    # Build last file hash map
    last_files = {f["path"]: f for f in last.get("files", [])}

    # Scan current
    current_files = scan_directory(root)
    current_map = {f["path"]: f for f in current_files}

    # Compare
    added = []
    modified = []
    removed = []
    unchanged = 0
    new_lines = 0
    deleted_lines = 0

    # Check for new and modified files
    for path, cur in current_map.items():
        if path not in last_files:
            added.append(path)
            new_lines += cur["lines"]
        elif cur["hash"] != last_files[path]["hash"]:
            diff = cur["lines"] - last_files[path]["lines"]
            if diff > 0:
                new_lines += diff
            elif diff < 0:
                deleted_lines += abs(diff)
            modified.append(path)
        else:
            unchanged += 1

    # Check for removed files
    for path in last_files:
        if path not in current_map:
            removed.append(path)
            deleted_lines += last_files[path]["lines"]

    return {
        "timestamp": datetime.now().isoformat(),
        "from_snapshot": str(snapshots[-1]),
        "file_count_change": len(current_files) - last.get("file_count", 0),
        "added_count": len(added),
        "modified_count": len(modified),
        "removed_count": len(removed),
        "unchanged_count": unchanged,
        "new_lines": new_lines,
        "deleted_lines": deleted_lines,
        "net_lines": new_lines - deleted_lines,
        "added_files": added[:10],
        "modified_files": modified[:10],
    }


def scan_files_and_grant(player: dict, root: str = ".") -> dict:
    """Scan files, compare with last snapshot, grant coding EXP.

    Returns:
        dict with diff info and exp granted
    """
    root = Path(root).resolve()

    diff = compare_snapshots(root)

    if diff is None:
        # First scan — just take a snapshot
        snap = save_snapshot(root)
        return {
            "success": True,
            "first_scan": True,
            "message": f"📸 首次扫描完成: {snap['file_count']} 个代码文件, {snap['total_lines']} 行代码\n再次扫描将自动记录 EXP",
            "files": snap["file_count"],
            "lines": snap["total_lines"],
            "exp_granted": 0,
            "levelup_msgs": [],
            "achievement_msgs": [],
        }

    # Calculate EXP for new lines (10 EXP per 100 lines)
    net_lines = diff["net_lines"]
    if net_lines > 0:
        streak = player.get("streak", 0)
        combo = player.get("combo", 0)
        exp = get_exp_for_action("coding_line", net_lines, streak, combo)
    else:
        exp = 0

    # Take new snapshot
    save_snapshot(root, f"scan_{date.today().isoformat()}")

    levelup_msgs = []
    ach_msgs = []
    if exp > 0:
        levelup_msgs = add_exp(player, exp)
        new_achievements = check_achievements(player)
        for ach in new_achievements:
            ach_msgs.append(f"🏆 成就解锁: {ach['name']} (+{ach['reward_exp']} EXP)")
        save_player(player)

    summary = f"""✅ 文件扫描完成:
  新增文件: {diff['added_count']}
  修改文件: {diff['modified_count']}
  删除文件: {diff['removed_count']}
  新增行数: +{diff['new_lines']}
  删除行数: -{diff['deleted_lines']}"""

    if exp > 0:
        summary += f"\n  → +{exp} EXP"
        summary += "\n" + "\n".join(levelup_msgs)
        if ach_msgs:
            summary += "\n" + "\n".join(ach_msgs)
    else:
        summary += "\n  (没有代码变化，无 EXP)"

    return {
        "success": True,
        "first_scan": False,
        "message": summary,
        "exp_granted": exp,
        "levelup_msgs": levelup_msgs,
        "achievement_msgs": ach_msgs,
        **diff,
    }


def get_file_status() -> str:
    """Get file tracking status summary."""
    snap_dir = get_snapshot_dir()
    snapshots = sorted(snap_dir.glob("snapshot_*.json"))

    lines = [
        "┌──────────────────────────────────────────┐",
        "│  📁 文件追踪状态                          │",
        "├──────────────────────────────────────────┤",
    ]

    if not snapshots:
        lines.append("│  尚未扫描过任何目录                    │")
        lines.append("│  使用 'shadow scan-files' 开始          │")
    else:
        with open(snapshots[-1], "r", encoding="utf-8") as f:
            last = json.load(f)

        lines.append(f"│  快照数: {len(snapshots)}                            │")
        lines.append(f"│  最新扫描: {last.get('label', 'N/A')[:20]}           │")
        lines.append(f"│  代码文件: {last.get('file_count', 0)}                         │")
        lines.append(f"│  代码行数: {last.get('total_lines', 0)}                        │")
        lines.append(f"│  快照位置: {str(snap_dir)[:30]}  │")

    lines.append("├──────────────────────────────────────────┤")
    lines.append(f"│  追踪扩展: {', '.join(sorted(CODE_EXTENSIONS)[:6])}     │")
    lines.append(f"│  ... 等 {len(CODE_EXTENSIONS)} 种                    │")
    lines.append("└──────────────────────────────────────────┘")

    return "\n".join(lines)
