from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Type
from typing_extensions import Self
from git_ai.cmd.constants import AIRepoConstants
from git_ai.pygitutils import get_repo_log, read_config
from pygit2 import Repository, Commit

from .ai_repo_config import InputRepo


class RecursiveLog:
    def __init__(self, repository: Optional[Repository]):
        self.repository = repository
        self.commits = []
        self.log: dict[str, dict[Path, Self]] = {}

    def add_commit(self, commit: Commit):
        self.commits.append(commit)
        self.log[str(commit.oid)] = {}

    def add_recursive_log(self, commit: Commit, input_repo: InputRepo, log: Self):
        self.log[str(commit.oid)][input_repo.path] = log

    def serialize_log(self, identation: str = "", input_repo_path: Path = Path("")) -> list[str]:
        serialized_log = []
        for commit in self.commits:
            short_oid = str(commit.oid)[:8]
            user = commit.author.name[:20]
            commit_tz = timezone(timedelta(minutes=commit.commit_time_offset))
            commit_at = datetime.fromtimestamp(
                commit.commit_time, tz=commit_tz).strftime("%Y-%m-%d %H:%M:%S")
            message = commit.message.strip("\n\t ")
            serialized_log.append("%s%s  %s %s %s" % (
                identation, short_oid, user, commit_at, message))
            paths = sorted(self.log[str(commit.oid)].keys())
            for path in paths:
                this_input_log = self.log[str(commit.oid)][path].serialize_log(
                    identation + "    ", input_repo_path / path)
                if this_input_log:
                    serialized_log.append(
                        "%s%s" % (identation, str(input_repo_path / path)))
                    serialized_log.extend(this_input_log)

        return serialized_log


class RootLog:
    def __init__(self, repository: Repository):
        if 'origin' not in repository.remotes:
            url = "local"
        else:
            url = str(repository.remotes['origin'].url)
        self.repository = repository
        self.repository_cache: dict[str, Repository] = {url: repository}
        self.commit_cache: dict[str, dict[str, Commit]] = {}

    def __get_input_repo_cache(self, input_repo: InputRepo) -> Repository:
        return self.__get_repo_cache(input_repo.uri, input_repo.path)

    def __get_repo_cache(self, uri: str, path: Path) -> Repository:
        if uri not in self.repository_cache:
            repo = Repository(path)
            self.repository_cache[uri] = repo
        else:
            repo = self.repository_cache[uri]
        return repo

    def __check_commit_cache(self, input_repo: InputRepo, commit: Commit) -> Optional[Commit]:
        if input_repo.uri in self.commit_cache:
            if str(commit.oid) not in self.repository_cache[input_repo.uri]:
                self.commit_cache[input_repo.uri][str(commit.oid)] = commit
                return commit
            else:
                return None
        else:
            return None

    def build_log(self, repo: Repository, commits: list[Commit]) -> RecursiveLog:
        log = RecursiveLog(repo)
        if len(commits) > 1:
            for this_c, next_c in zip(commits[:-1], commits[1:]):
                log.add_commit(this_c)
                self.__traverse_input_repos(repo, this_c, next_c, log)
        # TODO Add last commit
        if len(commits) >= 1:
            log.add_commit(commits[-1])

        return log

    def __get_input_repo_recursive_log(self, repo: Repository, input_repo: InputRepo, next_input_repo: Optional[InputRepo]) -> RecursiveLog:
        if next_input_repo:
            end_commit = next_input_repo.commit
        else:
            end_commit = None
        if end_commit:
            commit_list: list[Optional[Commit]] = get_repo_log(
                repo, input_repo.commit, end_commit)
            # end_commit is unreacheable from start_commit, return only 1 commit with a None
            # marking that there are more commits but a break in the list
            # if str(end_commit) != str(commit_list[-1].oid):
            #     commit_list += [None]
        else:
            commit_list: list[Optional[Commit]] = get_repo_log(
                repo, input_repo.commit)
        return self.build_log(repo, commit_list)

    def __traverse_input_repos(self, repo: Repository, this_c: Commit, next_c: Commit, log: RecursiveLog):
        this_config = read_config(repo, this_c.oid)
        next_config = read_config(repo, next_c.oid)

        if this_config:
            for input_repo in this_config.input_repos.values():
                input_repo_handle = Repository(
                    Path(repo.workdir) / input_repo.path)
                next_input_repo = (next_config.get_input_repo(input_repo.path)
                                   if next_config else None)
                if (next_input_repo and input_repo.commit != next_input_repo.commit) or not next_input_repo:
                    log.add_recursive_log(
                        this_c,
                        input_repo,
                        self.__get_input_repo_recursive_log(
                            input_repo_handle, input_repo, next_input_repo))


def build_log(repo: Repository, start_commit: str, end_commit: str = "") -> RecursiveLog:
    root_log = RootLog(repo)
    commits = get_repo_log(repo, start_commit, end_commit)
    return root_log.build_log(repo, commits)
