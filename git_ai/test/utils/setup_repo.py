from io import TextIOWrapper
from typing import Callable
import pygit2
from git_ai.cmd.ai_repo import AIRepo
import os
from pathlib import Path

current_path = Path(os.path.dirname(os.path.realpath(__file__)))


class SetupRepo:
    new_file_relative_path = 'newfile.txt'

    def __init__(self, root_folder: Path, name: str, main_branch='master') -> None:
        self.root_folder = root_folder
        self.name = name
        self.main_branch = main_branch
        os.makedirs(root_folder / name, exist_ok=True)
        self.bare_path = root_folder / name / "bare"
        self.copy_path = root_folder / name / "copy"

    def __create_test_repo(self) -> None:
        """creates a test repo in a temp folder. Adds test file to it.

        Returns handles for both the bare and the copy repository
        """
        self.copy_repo = pygit2.init_repository(self.copy_path)
        with open(os.path.join(self.copy_path, 'README.md'), 'w') as f:
            f.write('This is a test repository')

        self.copy_repo.index.add('README.md')
        self.copy_repo.index.write()
        self.copy_repo.create_commit(
            'HEAD', self.copy_repo.default_signature, self.copy_repo.default_signature, 'Initial commit', self.copy_repo.index.write_tree(), [])
        self.copy_repo.create_branch('main', self.copy_repo.head.peel())
        self.copy_repo.set_head('refs/heads/main')
        # Get the absolute path of the bare repo
        self.bare_repo = pygit2.init_repository(self.bare_path, bare=True)
        bare_path = os.path.abspath(self.bare_path)
        self.copy_repo.remotes.create(
            'origin', "file://%s" % bare_path)
        # Create main branch
        self.copy_repo.remotes['origin'].push(
            [f"refs/heads/main:refs/heads/main"])
        print(self.copy_repo.head)

    def change_file(self, change_fn: Callable[[TextIOWrapper], None], commit=False):
        copy = self.copy_repo
        new_file_path = Path(copy.workdir) / 'newfile.txt'
        with open(new_file_path, 'w') as f:
            change_fn(f)

        if commit:
            copy.index.read()
            copy.index.add(self.new_file_relative_path)
            copy.index.write()
            reference_name = 'refs/heads/main' if copy.head_is_unborn else copy.head.name
            parents = [] if copy.head_is_unborn else [copy.head.target]
            oid = copy.create_commit(
                reference_name,
                copy.default_signature,
                copy.default_signature,
                'commit test file',
                copy.index.write_tree(),
                parents
            )

            copy.head.set_target(oid)

    def __enter__(self):
        self.__create_test_repo()
        # Save current folder
        self.curr_folder = os.getcwd()
        # Change into repository folder
        os.chdir(self.copy_path)
        return self.copy_repo, self.bare_repo, self

    def __exit__(self, exec_type, exec_val, exec_tb):
        os.chdir(self.curr_folder)
        self.copy_repo.free()
        self.bare_repo.free()
        # shutil.rmtree(self.copy_path)
        # shutil.rmtree(self.bare_path)
