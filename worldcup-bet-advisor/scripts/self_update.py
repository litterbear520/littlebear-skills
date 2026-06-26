#!/usr/bin/env python3
"""self_update.py — 技能自更新（分发友好），SKILL.md 第 -1 步唯一入口。

两条路（启动自动判定）：
  1) 在 git 工作区（作者机 junction / clone 用户）：git pull --ff-only；工作区脏则只提示不强拉。
  2) 纯拷贝（npx skills / cp 装的第三方）：比对 GitHub 该技能目录最新 commit sha，
     有新版（或首次无缓存）就下 tarball、只解本技能子树、overlay 覆盖；保留本机私有文件。

设计要点：
  - fail-open：网络 / IO / git 任何异常都用当前版、绝不阻塞用户正事。
  - 每日缓存防抖：自拉路每天最多查一次 GitHub（.self_update.json 记 last_check_date）。
  - 作者不维护版本号：版本判定 = 该技能目录的最新 commit sha（commits API 带 path 过滤）。
输出契约（行首标记，供 SKILL.md / Claude 判断）：✓ updated / = up-to-date / ~ skipped / ⚠ dirty
完整设计见 docs/2026-06-23-self-update-design.md。
"""
from __future__ import annotations

import io
import json
import subprocess
import tarfile
import urllib.request
from datetime import date
from pathlib import Path

OWNER = "litterbear520"
REPO = "littlebear-skills"
SKILL_NAME = "worldcup-bet-advisor"

SKILL_DIR = Path(__file__).resolve().parents[1]
CACHE = SKILL_DIR / ".self_update.json"
TIMEOUT = 4          # 查版本用的短超时（秒）
DL_TIMEOUT = 30      # 下载 tarball 超时（秒）
UA = f"{SKILL_NAME}-self-update"

# 覆盖时保留的本机私有文件 / 目录（相对 SKILL_DIR）。这些都被 .gitignore，本不在 tarball 里，
# 这里再挡一道作为防御（万一上游误把 runs/ 提交进库，也不会删掉本机数据）。
PRESERVE_TOP = {"runs", ".self_update.json"}
PRESERVE_REL = set()


def log(msg: str) -> None:
    print(msg)


# ---------------------------------------------------------------- git 分支

def is_git_worktree(path: Path) -> bool:
    try:
        r = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=TIMEOUT,
        )
        return r.returncode == 0 and r.stdout.strip() == "true"
    except Exception:
        return False


def git_update(skill_dir: Path) -> str:
    """作者机 / clone 用户：在 skill 目录所属仓库做 ff-only pull。返回输出契约字符串。

    全部用 `git -C skill_dir`，让 git 自己解析仓库根（透明穿透 junction/软链），
    避免手算跨盘相对路径。脏检查用 `-- .` 只看本 skill 目录、不被同仓库其他技能干扰。
    """
    g = ["git", "-C", str(skill_dir)]
    try:
        if subprocess.run(g + ["fetch", "-q", "origin"], capture_output=True,
                          text=True, timeout=DL_TIMEOUT).returncode != 0:
            return "~ skipped (连不上 GitHub，用本地版)"
        br = subprocess.run(g + ["rev-parse", "--abbrev-ref", "HEAD"],
                            capture_output=True, text=True, timeout=TIMEOUT).stdout.strip()
        if not br or subprocess.run(g + ["rev-parse", "--verify", "-q", f"origin/{br}"],
                                    capture_output=True, text=True, timeout=TIMEOUT).returncode != 0:
            return f"~ skipped (无 origin/{br or '?'})"
        behind = subprocess.run(g + ["rev-list", "--count", f"{br}..origin/{br}"],
                                capture_output=True, text=True, timeout=TIMEOUT).stdout.strip() or "0"
        if behind == "0":
            return "= up-to-date"
        dirty = subprocess.run(g + ["status", "--porcelain", "--", "."],
                               capture_output=True, text=True, timeout=TIMEOUT).stdout.strip()
        if dirty:
            return "⚠ dirty (本地有未提交改动，先 git commit/push 再更新)"
        if subprocess.run(g + ["pull", "--ff-only", "-q", "origin", br],
                          capture_output=True, text=True, timeout=DL_TIMEOUT).returncode != 0:
            return "~ skipped (本地与远端分叉，用本地版)"
        return f"✓ updated (git pull，{behind} 个新提交)"
    except Exception:
        return "~ skipped (git 异常，用本地版)"


# ---------------------------------------------------------------- 自拉分支

def remote_latest_sha(timeout: int = TIMEOUT) -> str | None:
    """该技能目录的最新 commit sha（commits API 带 path 过滤，匿名访问）。失败返回 None。"""
    url = (f"https://api.github.com/repos/{OWNER}/{REPO}/commits"
           f"?path={SKILL_NAME}&per_page=1")
    req = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if isinstance(data, list) and data:
        return data[0].get("sha")
    return None


def fetch_tarball(sha: str, timeout: int = DL_TIMEOUT) -> bytes:
    url = f"https://codeload.github.com/{OWNER}/{REPO}/tar.gz/{sha}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def extract_subtree(raw: bytes, dest: Path) -> int:
    """从 repo tarball 字节里只解出 `*/<SKILL_NAME>/` 子树，overlay 覆盖到 dest。

    - 跳过本机私有文件（PRESERVE_*）与 __pycache__
    - 防 tar 路径穿越：解析后的目标必须落在 dest 内
    返回写入的文件数（便于测试断言）。
    """
    dest = dest.resolve()
    marker = f"/{SKILL_NAME}/"
    written = 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tf:
        for m in tf.getmembers():
            idx = m.name.find(marker)
            if idx == -1:
                continue
            rel = m.name[idx + len(marker):]
            if not rel:
                continue
            if rel in PRESERVE_REL or rel.split("/", 1)[0] in PRESERVE_TOP:
                continue
            if "__pycache__" in rel:
                continue
            target = (dest / rel).resolve()
            if dest not in target.parents and target != dest:
                continue  # 防穿越
            if m.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif m.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                src = tf.extractfile(m)
                if src is not None:
                    target.write_bytes(src.read())
                    written += 1
    return written


# ---------------------------------------------------------------- 缓存

def read_cache() -> dict:
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_cache(d: dict) -> None:
    try:
        CACHE.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


# ---------------------------------------------------------------- 主流程

def self_update() -> str:
    try:
        if is_git_worktree(SKILL_DIR):
            msg = git_update(SKILL_DIR)
            log(msg)
            return msg

        today = date.today().isoformat()
        cache = read_cache()
        if cache.get("last_check_date") == today:
            log("~ skipped (今日已查)")
            return "~ skipped"

        try:
            sha = remote_latest_sha()
        except Exception:
            sha = None
        if not sha:
            write_cache({**cache, "last_check_date": today})
            log("~ skipped (连不上 GitHub，用本地版)")
            return "~ skipped"

        if cache.get("current_sha") == sha:
            write_cache({"current_sha": sha, "last_check_date": today})
            log("= up-to-date")
            return "= up-to-date"

        # 有新版，或首次无缓存 → 下载对齐
        try:
            extract_subtree(fetch_tarball(sha), SKILL_DIR)
        except Exception:
            write_cache({**cache, "last_check_date": today})
            log("~ skipped (下载失败，用本地版)")
            return "~ skipped"

        write_cache({"current_sha": sha, "last_check_date": today})
        msg = f"✓ updated ({sha[:7]})"
        log(msg)
        return msg
    except Exception:
        log("~ skipped (自更新异常，用本地版)")
        return "~ skipped"


if __name__ == "__main__":
    self_update()
