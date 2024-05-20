from pathlib import Path
from typing import Optional, Union
import pygit2
from pygit2 import Repository, Oid, Commit
from git_ai.cmd.constants import AIRepoConstants
from git_ai.cmd.ai_repo.ai_repo_config import AIRepoConfig
import os


def get_repo_log(repo: Repository, start_commit: Union[str, Oid] = "", end_commit: Union[str, Oid] = "") -> list[Optional[Commit]]:
    commits = []
    for c in repo.walk(start_commit, pygit2.GIT_SORT_TOPOLOGICAL):
        if end_commit and end_commit in c.oid.hex:
            break
        commits.append(c)
    return commits


def read_config(repo: Repository, oid: Union[str, Oid] = "") -> Optional[AIRepoConfig]:
    if not oid:
        config_path = Path(repo.workdir) / AIRepoConstants.CONFIG_PATH
        return AIRepoConfig.from_file(config_path) if os.path.isfile(config_path) else None

    else:
        commit = repo.get(oid)
        if AIRepoConstants.CONFIG_PATH in commit.tree:   # type: ignore
            config_file = commit.tree / AIRepoConstants.CONFIG_PATH   # type: ignore
            return AIRepoConfig.from_str(config_file.data)
