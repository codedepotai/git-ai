import os
from git_ai.cmd.ai_repo import AIRepo


def merge_exp(args):
    ai_repo = AIRepo(os.getcwd())
    ai_repo.merge_experiment(args[2], "")
