"""Check tracked working files and Git blob history for the configured Meta key."""
from pathlib import Path
import os
import shutil
import subprocess

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def check():
    git = shutil.which("git")
    if not git:
        fallback = Path.home()/".cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe"
        if fallback.is_file():
            git = str(fallback)
    if not git:
        raise RuntimeError("Git is required for the history check.")
    def run(*args):
        return subprocess.check_output([git,*args],cwd=ROOT)
    tracked = run("ls-files","-z").decode().split("\0")
    forbidden = [name for name in tracked if name and (name==".env" or name.startswith((".data/",".venv/","work/")) or "/node_modules/" in name)]
    assert not forbidden, "Sensitive/runtime paths are tracked."
    key = os.getenv("MODEL_API_KEY") or dotenv_values(ROOT/".env").get("MODEL_API_KEY")
    if not key:
        raise RuntimeError("No configured key available for exact-match scanning.")
    needle = key.encode()
    checked = 0
    for name in tracked:
        if name and (ROOT/name).is_file():
            assert needle not in (ROOT/name).read_bytes(), "Credential found in tracked file."
    objects = run("rev-list","--objects","--all").decode().splitlines()
    for entry in objects:
        identifier = entry.split(" ",1)[0]
        if run("cat-file","-t",identifier).strip() == b"blob":
            assert needle not in run("cat-file","blob",identifier), "Credential found in Git history."
            checked += 1
    print(f"PASS: configured key absent from tracked files and {checked} historical Git blobs; runtime paths excluded.")


if __name__=="__main__":
    check()
