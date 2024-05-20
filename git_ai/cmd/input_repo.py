import os
from pathlib import Path
from git_ai.cmd.ai_repo import AIRepo


def input_repo(args):
    ai_repo = AIRepo(os.getcwd())
    if args[2] == 'add':
        commit = args[5] if len(args) == 6 else ""
        ai_repo.add_input_repo(Path(args[3]), args[4], commit)
    elif args[2] == 'update':
        ai_repo.update_input_repo(Path(args[3]), commit_spec=args[4])
