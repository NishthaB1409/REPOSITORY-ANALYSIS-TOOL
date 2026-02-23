# gitlab_api.py
import requests
from urllib.parse import quote_plus
from urllib.parse import parse_qs, urlparse
import subprocess

GITLAB_API_URL = "https://gitlab.com/api/v4"
REQUEST_TIMEOUT_SECONDS = 20


# ---------------------- GitLab API functions ---------------------- #

def extract_project_path(repo_url: str) -> str:
    """
    Extract namespace/project from GitLab URL
    """
    if "gitlab.com/" not in repo_url:
        raise ValueError("Invalid GitLab repository URL")
    return repo_url.split("gitlab.com/")[1].strip("/")


def get_project_info(project_path: str) -> dict:
    """
    Fetch project metadata from GitLab
    """
    encoded_path = quote_plus(project_path)
    response = requests.get(
        f"{GITLAB_API_URL}/projects/{encoded_path}",
        params={"license": "true"},
        timeout=REQUEST_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    return response.json()


def get_forks(project_id: int) -> list:
    """
    Fetch all forks of a project
    """
    response = requests.get(
        f"{GITLAB_API_URL}/projects/{project_id}/forks",
        params={"per_page": 30},
        timeout=REQUEST_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    return response.json()


def get_project_info_by_id(project_id: int) -> dict:
    """
    Fetch project metadata by project ID from GitLab
    """
    response = requests.get(
        f"{GITLAB_API_URL}/projects/{project_id}",
        params={"license": "true"},
        timeout=REQUEST_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    return response.json()


def get_branch_names(project_id: int) -> list:
    """
    Fetch all branch names for a project using GitLab API pagination.
    """
    branches = []
    page = 1

    while True:
        response = requests.get(
            f"{GITLAB_API_URL}/projects/{project_id}/repository/branches",
            params={"per_page": 100, "page": page},
            timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        batch = response.json()
        branches.extend(branch.get("name") for branch in batch if branch.get("name"))

        next_page = response.headers.get("X-Next-Page")
        if not next_page:
            break
        page = int(next_page)

    return branches


def get_total_commit_count(project_id: int, branch: str = None) -> int:
    """
    Returns total commit count for a branch (or default branch).
    Uses X-Total when available; falls back to Link header parsing.
    """
    per_page = 100
    params = {"per_page": per_page}
    if branch:
        params["ref_name"] = branch

    response = requests.get(
        f"{GITLAB_API_URL}/projects/{project_id}/repository/commits",
        params=params,
        timeout=REQUEST_TIMEOUT_SECONDS
    )
    response.raise_for_status()

    total_header = response.headers.get("X-Total")
    if total_header is not None:
        return int(total_header)

    total_pages_header = response.headers.get("X-Total-Pages")
    if total_pages_header is not None:
        total_pages = int(total_pages_header)
        if total_pages <= 1:
            commits = response.json()
            return len(commits) if isinstance(commits, list) else 0

        last_page_response = requests.get(
            f"{GITLAB_API_URL}/projects/{project_id}/repository/commits",
            params={**params, "page": total_pages},
            timeout=REQUEST_TIMEOUT_SECONDS
        )
        last_page_response.raise_for_status()
        last_page_commits = last_page_response.json()
        last_page_count = len(last_page_commits) if isinstance(last_page_commits, list) else 0
        return (total_pages - 1) * per_page + last_page_count

    # Fallback for GitLab responses that omit X-Total/X-Total-Pages.
    last_link = response.links.get("last", {}).get("url")
    if last_link:
        last_page = parse_qs(urlparse(last_link).query).get("page", [None])[0]
        if last_page is not None:
            last_page_int = int(last_page)
            last_page_response = requests.get(
                f"{GITLAB_API_URL}/projects/{project_id}/repository/commits",
                params={**params, "page": last_page_int},
                timeout=REQUEST_TIMEOUT_SECONDS
            )
            last_page_response.raise_for_status()
            last_page_commits = last_page_response.json()
            last_page_count = len(last_page_commits) if isinstance(last_page_commits, list) else 0
            return (last_page_int - 1) * per_page + last_page_count

    commits = response.json()
    if not isinstance(commits, list):
        return 0

    # If there is no next page, page 1 already contains the full result.
    if "next" not in response.links:
        return len(commits)

    def page_size(page: int) -> int:
        page_params = {"per_page": per_page, "page": page}
        if branch:
            page_params["ref_name"] = branch

        page_response = requests.get(
            f"{GITLAB_API_URL}/projects/{project_id}/repository/commits",
            params=page_params,
            timeout=REQUEST_TIMEOUT_SECONDS
        )
        if page_response.status_code != 200:
            return 0

        page_commits = page_response.json()
        if not isinstance(page_commits, list):
            return 0
        return len(page_commits)

    # When GitLab only exposes "next", use bounded probing to stay fast.
    low = 1
    high = 10
    high_size = page_size(high)
    while high_size > 0 and high < 1_000_000:
        low = high
        high *= 10
        high_size = page_size(high)

    # Bounded binary search (6 iterations) keeps speed acceptable
    # while giving more accurate counts for ranking.
    for _ in range(6):
        if low + 1 >= high:
            break
        mid = (low + high) // 2
        if page_size(mid) > 0:
            low = mid
        else:
            high = mid

    last_page_count = page_size(low)
    return (low - 1) * per_page + last_page_count


# ---------------------- Local git utilities ---------------------- #

def list_branches(repo_dir: str) -> list:
    """
    List all branches in a local repository
    """
    result = subprocess.run(
        ["git", "branch", "-a"],
        cwd=repo_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if result.returncode != 0:
        raise Exception(result.stderr)

    return [
        line.strip().replace("* ", "")
        for line in result.stdout.splitlines()
    ]


def get_active_branch(repo_dir: str) -> str:
    """
    Get active branch of local repository
    """
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if result.returncode != 0:
        raise Exception(result.stderr)

    return result.stdout.strip()
