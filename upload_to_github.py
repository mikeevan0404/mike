#!/usr/bin/env python3
"""用 GitHub API 创建仓库并上传 tg-group-manager-bot 全部代码（无需安装 git）。

用法: GH_TOKEN=ghp_xxx python3 upload_to_github.py [仓库名]
默认仓库名: tg-group-manager-bot；若用户此前指定的 mike 仓库存在则优先使用。
"""
import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

TOKEN = os.environ.get("GH_TOKEN", "").strip()
OWNER = os.environ.get("GH_OWNER", "mikeevan0404")
PROJECT = Path(__file__).resolve().parent

# 与 .gitignore / .dockerignore 保持一致
EXCLUDE_DIRS = {".git", ".venv", "data", "__pycache__", ".sessions"}
EXCLUDE_FILES = {".env", "*.pyc", ".DS_Store"}
EXCLUDE_SUFFIX = {".pyc"}

DEFAULT_REPO = "tg-group-manager-bot"
PREFERRED_REPO = "mike"  # 用户提供的仓库链接


def api(method: str, url: str, body: dict | None = None) -> dict | None:
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    data = json.dumps(body).encode() if body is not None else None
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data=data, timeout=30) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="ignore")
        if e.code in (404,):
            return None
        if e.code in (409, 422) and "already_exists" in detail:
            return {"exists": True}
        print(f"  [HTTP {e.code}] {url}\n  {detail[:300]}", file=sys.stderr)
        raise


def repo_exists(name: str) -> bool:
    return api("GET", f"https://api.github.com/repos/{OWNER}/{name}") is not None


def create_repo(name: str) -> bool:
    print(f"创建仓库 {OWNER}/{name} …")
    r = api("POST", "https://api.github.com/user/repos",
            {"name": name, "private": False, "auto_init": False, "description": "Telegram 群管机器人（Python + aiogram + Docker）"})
    return r is not None


def _file_sha(repo: str, path: str) -> str | None:
    r = api("GET", f"https://api.github.com/repos/{OWNER}/{repo}/contents/{path}")
    return r["sha"] if r else None


def upload_file(repo: str, rel: Path, content: bytes) -> None:
    url = f"https://api.github.com/repos/{OWNER}/{repo}/contents/{rel.as_posix()}"
    body = {"message": f"upload {rel.as_posix()}", "content": base64.b64encode(content).decode()}
    sha = _file_sha(repo, rel.as_posix())
    if sha:  # 文件已存在：更新必须携带 sha
        body["sha"] = sha
    api("PUT", url, body)


def collect_files() -> list[Path]:
    files = []
    for p in sorted(PROJECT.rglob("*")):
        if p.is_dir():
            continue
        parts = set(p.relative_to(PROJECT).parts)
        if parts & EXCLUDE_DIRS:
            continue
        name = p.name
        if name in EXCLUDE_FILES or p.suffix in EXCLUDE_SUFFIX:
            continue
        files.append(p)
    return files


def main() -> None:
    if not TOKEN:
        print("错误：请设置环境变量 GH_TOKEN=ghp_xxx 后运行")
        sys.exit(1)

    repo = DEFAULT_REPO
    if repo_exists(PREFERRED_REPO):
        repo = PREFERRED_REPO
        print(f"检测到已有仓库 {OWNER}/{PREFERRED_REPO}，将上传到该仓库")
    elif not repo_exists(DEFAULT_REPO):
        if not create_repo(DEFAULT_REPO):
            print("创建仓库失败，退出")
            sys.exit(1)
    else:
        print(f"使用已有仓库 {OWNER}/{DEFAULT_REPO}")

    files = collect_files()
    print(f"共 {len(files)} 个文件，开始上传…")
    for i, p in enumerate(files, 1):
        rel = p.relative_to(PROJECT)
        upload_file(repo, rel, p.read_bytes())
        print(f"  [{i}/{len(files)}] {rel.as_posix()}")
    print("✅ 全部上传完成")


if __name__ == "__main__":
    main()
