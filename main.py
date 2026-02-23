# main.py
import os
import shutil
import stat
import subprocess
import tempfile
import json
from concurrent.futures import ThreadPoolExecutor

from gitlab_api import (
    extract_project_path,
    get_project_info,
    get_project_info_by_id,
    get_branch_names,
    get_forks,
    get_total_commit_count,
)

MAX_FORKS_TO_ANALYZE = 5


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

    forks = get_forks(project_id)[:MAX_FORKS_TO_ANALYZE]
    total_forks = project.get("forks_count", len(forks))

    total_commits = get_total_commit_count(project_id, branch=default_branch)
    branches = get_branch_names(project_id)
    active_branch = default_branch

    # Analyze forks
    def analyze_fork(fork: dict) -> dict:
        fork_id = fork["id"]
        try:
            fork_project = get_project_info_by_id(fork_id)
            fork_default_branch = fork_project.get("default_branch")
            commit_count = get_total_commit_count(
                fork_id,
                branch=fork_default_branch
            )
            fork_license = (fork_project.get("license") or {}).get("name")
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

    max_workers = min(8, len(forks)) if forks else 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        fork_stats = list(executor.map(analyze_fork, forks))

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
