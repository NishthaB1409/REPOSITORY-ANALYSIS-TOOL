# main.py
import os
import shutil
import stat
import subprocess
import tempfile
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from gitlab_api import (
    extract_project_path,
    get_project_info,
    get_project_info_by_id,
    get_branch_names,
    get_forks,
    get_total_commit_count,
)

MAX_FORKS_TO_ANALYZE = 5
_commit_count_cache = {}
_commit_count_cache_lock = Lock()


# ---------------------- Local git helpers ---------------------- #

def count_commits_local(repo_dir: str) -> int:
    """
    Count commits in the current branch of a cloned repository
    """
    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=repo_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if result.returncode != 0:
        raise Exception(result.stderr)

    return int(result.stdout.strip())


def remove_readonly(func, path, excinfo):
    """
    Fix Windows permission issues when deleting temp folders
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)


# ---------------------- Core analysis logic ---------------------- #

def get_commit_count_cached(project_id: int, branch: str, activity_marker: str) -> int:
    """
    Cache commit counts for unchanged repositories/branches.
    """
    cache_key = (project_id, branch, activity_marker)
    with _commit_count_cache_lock:
        cached_count = _commit_count_cache.get(cache_key)
    if cached_count is not None:
        return cached_count

    commit_count = get_total_commit_count(project_id, branch=branch)
    with _commit_count_cache_lock:
        _commit_count_cache[cache_key] = commit_count
    return commit_count

def analyze_repository(repo_url: str) -> dict:
    """
    Main analysis function (UI / REST ready)
    """
    project_path = extract_project_path(repo_url)
    project = get_project_info(project_path)

    project_id = project["id"]
    project_name = project["name"]
    default_branch = project.get("default_branch", "main")
    license_info = project.get("license", {}).get("name")
    project_last_activity = project.get("last_activity_at", "")

    # Fetch forks first, then overlap project-level work with fork analysis.
    forks = get_forks(project_id)[:MAX_FORKS_TO_ANALYZE]
    total_forks = project.get("forks_count", len(forks))
    active_branch = default_branch

    # Analyze forks
    def analyze_fork(fork: dict) -> dict:
        fork_id = fork["id"]
        try:
            fork_default_branch = fork.get("default_branch")
            fork_license = (fork.get("license") or {}).get("name")

            # Fallback only when the forks payload is incomplete.
            if fork_default_branch is None or fork_license is None:
                fork_project = get_project_info_by_id(fork_id)
                if fork_default_branch is None:
                    fork_default_branch = fork_project.get("default_branch")
                if fork_license is None:
                    fork_license = (fork_project.get("license") or {}).get("name")

            commit_count = get_commit_count_cached(
                fork_id,
                fork_default_branch,
                fork.get("last_activity_at", "")
            )
        except Exception:
            commit_count = 0
            fork_license = None

        return {
            "name": fork["path_with_namespace"],
            "commits": commit_count,
            "license": fork_license,
            "last_updated": fork["last_activity_at"],
            "active": commit_count > 0
        }

    fork_workers = min(8, len(forks)) if forks else 1
    total_workers = max(3, fork_workers + 2)
    with ThreadPoolExecutor(max_workers=total_workers) as executor:
        total_commits_future = executor.submit(
            get_commit_count_cached,
            project_id,
            default_branch,
            project_last_activity
        )
        branches_future = executor.submit(get_branch_names, project_id)
        fork_stats = list(executor.map(analyze_fork, forks))
        total_commits = total_commits_future.result()
        branches = branches_future.result()

    most_active_fork = max(
        fork_stats,
        key=lambda f: f["commits"],
        default=None
    )

    return {
        "project": {
            "name": project_name,
            "default_branch": default_branch,
            "license": license_info,
            "total_commits": total_commits
        },
        "branches": {
            "all": branches,
            "active": active_branch
        },
        "forks": {
            "count": total_forks,
            "analyzed_count": len(fork_stats),
            "details": fork_stats,
            "most_active": most_active_fork
        }
    }


# ---------------------- CLI entry point ---------------------- #

if __name__ == "__main__":
    repo_url = input("Enter public GitLab repository URL: ").strip()

    try:
        result = analyze_repository(repo_url)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"❌ Error: {e}")
