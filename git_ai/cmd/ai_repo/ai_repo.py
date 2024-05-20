import json
import os
from pathlib import Path
from typing import Optional, Union

import pygit2
from pygit2 import AlreadyExistsError, Repository, discover_repository

from git_ai.errors.errors import AlreadyInitializedError, CommitError, CommitSignatureError
from .ai_repo_config import AIRepoConfig, InputRepo
from .ai_repo_log import RecursiveLog, build_log
from git_ai.cmd.constants import AIRepoConstants
from git_ai.errors import CorruptedRepoError
from ...utils import list_path
from .credentials import Credentials

from git_ai.pygitutils import get_repo_log, read_config


class AIRepo(Repository, AIRepoConstants):
    # TODO Add logging capabilities
    def __init__(self, path: str | None = None):
        super().__init__(discover_repository(path if path else os.getcwd()))
        self.credentials = Credentials(self)

    def auth_and_fetch(self, remote):
        self.credentials.auth_operation(
            self.remotes[remote].url, lambda cred: self.remotes[remote].fetch(callbacks=cred))

    def auth_and_push(self, remote, qualified_branch):
        self.credentials.auth_operation(self.remotes[remote].url, lambda cred: self.remotes[remote].push(
            [f"{qualified_branch}:{qualified_branch}"], callbacks=cred))

    def remove_ai_dirs(self):
        try:
            os.rmdir(self.GIT_AI_ROOT)
        except:
            pass

    def make_ai_dirs(self):
        os.makedirs(self.GIT_AI_ROOT, exist_ok=True)
        os.makedirs(self.METRICS_PATH, exist_ok=True)
        os.makedirs(self.ARTIFACT_PATH, exist_ok=True)

    def init_ai_repo(self):
        if os.path.isfile(self.CONFIG_PATH):
            AlreadyInitializedError.repository_already_initialized()

        self.make_ai_dirs()

        if os.path.isfile(self.CONFIG_PATH):
            if self.CONFIG_PATH in self.index:
                raise CorruptedRepoError.corrupted_uncommited_config()
            else:
                raise CorruptedRepoError.corrupted_commited_config()

        config_json = AIRepoConfig.default().serialize()

        with open(self.CONFIG_PATH, 'w') as f:
            json.dump(config_json, f)

        self.commit([self.CONFIG_PATH], [], "Initializing AI Repo")

    def get_current_branch(self):
        try:
            return self.head.name
        # If the repo is empty, pygit2.GitError is raised
        except pygit2.GitError:
            # Read from the config
            if 'init.defaultBranch' in self.config:
                return self.config['init.defaultBranch']
            else:
                return 'refs/heads/main'

    def checkout_branch(self, name: str, new: bool = False):
        if new:
            commit = self.revparse_single('HEAD')
            branch = self.branches.local.create(name, commit)
        else:
            if name.startswith('refs/heads/'):
                name = name.replace('refs/heads/', '')
            branch = self.lookup_branch(name)
        ref = self.lookup_reference(branch.name)
        self.checkout(ref)

    def is_ai_initialized(self) -> bool:
        return not self.is_empty and self.CONFIG_PATH in self.get(self.head.target).tree

    def commit(self, path_add_list: list[Union[str, Path]], path_remove_list: list[Union[str, Path]],
               message: str):
        if not path_add_list and not path_remove_list:
            return

        file_list = [f for path in path_add_list for f in list_path(path)]
        # Create objects in the tree
        # Create index
        self.index.read()
        for f in file_list:
            try:
                self.index.add(f)
            except pygit2.GitError:
                raise CommitError.g_to_stage(f)

        for f in path_remove_list:
            self.index.remove(f)

        self.index.write()
        t = self.index.write_tree()

        # Make commit
        try:
            user = self.default_signature
        except Exception:
            raise CommitSignatureError.missing_signature()
        reference_name = self.get_current_branch()
        parents = [] if self.is_empty else [self.head.target]
        oid = self.create_commit(
            reference_name,
            user,
            user,
            message,
            t,
            parents
        )
        if self.is_empty:
            self.head.set_target(oid)

    # isinstance(commit, Object)
    def list_file_contents(self, commit_oid: str, path: str):
        # TODO What if path points to a tree
        tree = self.revparse_single(commit_oid).tree  # type: ignore
        if path in tree:
            return tree[path].data.decode("utf-8")
        else:
            return None

    def list_repo_folder(self, folder_path_in_repo: Path = Path('.'),
                         exclude_list: list[str] = []) -> list[tuple[Path, str]]:
        repo_root = Path(self.workdir)
        all_files = os.listdir(repo_root / folder_path_in_repo)

        file_list = []
        for f in all_files:
            curr_file_path = (folder_path_in_repo / f
                              if (str(folder_path_in_repo) != '.') else f)
            if str(curr_file_path) not in exclude_list:
                file_list.append((folder_path_in_repo, f))
                if (os.path.isdir(repo_root / folder_path_in_repo / f)):
                    file_list.extend(
                        self.list_repo_folder(folder_path_in_repo / f, exclude_list))
        return file_list

    @ staticmethod
    def unroll_sub_tree(subtree, curr_path: Path, keep_trees: bool):
        entries = []
        for entry in subtree:
            if entry.filemode == pygit2.GIT_FILEMODE_TREE:
                if keep_trees:
                    entries.append((entry, curr_path))
                next_path = curr_path / entry.name
                entries.extend(AIRepo.unroll_sub_tree(
                    entry, next_path, keep_trees))
            else:
                entries.append((entry, curr_path))

        return entries

    def merge_experiment(self, exp_name: str, message: str) -> None:
        """Merges an experiment, bringing all the files in .git_ai from the experiment.
        Warns if the current branch has other changes that will not be merged.
        This is not a merge as it picks files from another commits and directly overwrites them
        into this commit.
        TODO
            handle case where repository is dirty
            warn user if experiment commit has other changes then those in .git_ai
        Args:
            exp_name (str): Name of the experiment to be merged
            branch_name (Optional[str], optional): Name of the branch where the the experiment will be merged.
                Defaults to None.
        """
        config = read_config(self)
        experiment_last_commit = self.get(
            self.branches['exp/%s' % exp_name].target)
        new_config = read_config(self, experiment_last_commit.oid)
        experiment = experiment_last_commit.tree / self.GIT_AI_ROOT   # type: ignore
        experiment_git_ai_files = AIRepo.unroll_sub_tree(
            experiment, Path(self.GIT_AI_ROOT), keep_trees=True)
        repo_head_commit = self.get(self.head.target)
        repo_entries = AIRepo.unroll_sub_tree(
            repo_head_commit.tree / self.GIT_AI_ROOT,    # type: ignore
            Path(self.GIT_AI_ROOT),
            keep_trees=False)
        experiment_git_ai_files_set = set([
            path / obj.name for obj, path in experiment_git_ai_files
        ])
        repo_entries = set([
            path / obj.name for obj, path in repo_entries
        ])

        removed_files = [
            p for p in repo_entries if p not in experiment_git_ai_files_set]
        added_files = [
            p for p in experiment_git_ai_files_set if p not in removed_files]

        # Create all the files
        for e, path in experiment_git_ai_files:
            if e.filemode == pygit2.GIT_FILEMODE_TREE:
                os.makedirs(Path(self.workdir) / path / e.name, exist_ok=True)
            else:
                permissions = (0o755 if e.filemode == pygit2.GIT_FILEMODE_BLOB_EXECUTABLE
                               else 0o644)
                with open(Path(self.workdir) / path / e.name, 'wb') as f:
                    f.write(e.data)
                os.chmod(Path(self.workdir) / path / e.name, mode=permissions)

        self.merge_config(config, new_config)
        if not message:
            message = "Merging experiment %s" % exp_name
        self.commit(added_files, removed_files, message)

    def add_input_repo(self, submodule_path: Path, remote_uri: str, commit_spec: Optional[str] = None, commit: bool = True) -> None:
        """Adds an input repository to the current repo

        Args:
            remote_path (Union[str, Path]): relative path to the remote repo
            remote_uri (str): uri to the repository
            commit_spec (Optional[str], optional): Commit in the remote repo to be cloned. Defaults to None which clones the head.
        """
        config = read_config(self)
        # TODO What if config is not true

        sub = self.credentials.auth_operation(
            remote_uri,
            lambda cred: self.submodules.add(
                url=remote_uri, path=submodule_path, callbacks=cred, link=False)
        )
        sub_repo = pygit2.Repository(sub.path)
        input_repo_commit = str(commit_spec) if commit_spec else str(
            sub_repo.head.target)
        config.add_input_repo(input_repo=InputRepo(
            path=submodule_path, uri=remote_uri, commit=input_repo_commit))
        self.write_config(config)

        if commit_spec:
            self.update_input_repo(
                submodule_path, commit_spec=commit_spec, commit=False)
        if commit:
            self.commit(
                path_add_list=[self.CONFIG_PATH], path_remove_list=[],
                message="Adding input repo %s with url %s" % (submodule_path, remote_uri))

    def update_input_repo(self, submodule_path: Union[str, Path], remote_uri: str = '', commit_spec: Optional[str] = None, commit=True) -> None:
        """Adds an input repository to the current repo
        TODO: handle change of url
        Args:
            remote_path (Union[str, Path]): relative path to the remote repo
            remote_uri (str): uri to the repository
            commit_spec (Optional[str], optional): Commit in the remote repo to be cloned. Defaults to None which clones the head.
        """
        submodule_repo = Repository(
            Path(self.workdir) / submodule_path)
        submodule_commit = submodule_repo[commit_spec]
        submodule_repo.checkout_tree(submodule_commit)
        submodule_repo.set_head(submodule_commit.oid)

        config = read_config(self)
        config.update_input_repo(Path(submodule_path), commit=commit_spec)
        self.write_config(config)

        # FIXME HUGE HACK!
        os.system('git add %s' % submodule_path)
        # self.index.add(submodule_path)
        if commit:
            self.commit(path_add_list=[self.CONFIG_PATH], path_remove_list=[],
                        message="Updating input repo %s to point to %s" %
                        (submodule_path, commit_spec))

    def remove_input_repo(self, submodule_path: Union[str, Path], remote_uri: str = '', commit_spec: Optional[str] = None, commit=True) -> None:
        """Removes an input repo

        Args:
            submodule_path (Union[str, Path]): Path to submodule
            remote_uri (str, optional): Uri for remote. Defaults to ''.
            commit_spec (Optional[str], optional): Spec to commit. Defaults to None.
            commit (bool, optional): Bool to decide wheter to commit the removeal or not. Defaults to True.

        """
        pass

    def write_config(self, config: AIRepoConfig):
        with open(Path(self.workdir) / self.CONFIG_PATH, 'w') as f:
            json.dump(config.serialize(), f)

    def merge_config(self, old_config: AIRepoConfig, new_config: AIRepoConfig):
        for new_path, new_input_repo in new_config.input_repos.items():
            if new_path in old_config.input_repos:
                self.update_input_repo(
                    new_path, new_input_repo.uri, new_input_repo.commit, commit=False)
            else:
                self.add_input_repo(new_input_repo.path,
                                    new_input_repo.uri, new_input_repo.commit, commit=False)

        for old_path, old_input_repo in old_config.input_repos.items():
            if old_path not in new_config.input_repos:
                # TODO need to remove the input repo
                pass

        self.write_config(new_config)

    def get_wt_modified_files(self) -> tuple[list[str], list[str], list[str], list[str]]:
        status = self.status()
        new = []
        modified = []
        removed = []
        renamed = []
        for filepath, flags in status.items():
            if flags and pygit2.GIT_STATUS_WT_NEW:
                new.append(filepath)
            elif flags and pygit2.GIT_STATUS_WT_MODIFIED:
                modified.append(filepath)
            elif flags and pygit2.GIT_STATUS_WT_DELETED:
                removed.append(filepath)
            elif flags and pygit2.GIT_STATUS_WT_RENAMED:
                renamed.append(filepath)

        return new, modified, removed, renamed

    def get_ai_modified_files(self) -> tuple[list[str], list[str]]:
        new, modified, removed, _ = self.get_wt_modified_files()
        to_add = self.filter_ai_repo_files(new + modified)
        to_remove = self.filter_ai_repo_files(removed)
        return to_add, to_remove

    def get_log(self, start_commit: str = "", end_commit: str = "") -> RecursiveLog:
        if not start_commit:
            start_commit = str(self.head.target)
        return build_log(self, start_commit, end_commit)
