import os
from git_ai.cmd.ai_repo import AIRepo


def log(args):
    ai_repo = AIRepo(os.getcwd())
    commit_spec = str(ai_repo.head.target) if len(args) < 3 else args[2]
    commit, _ = ai_repo.resolve_refish(commit_spec)
    for line in ai_repo.get_log(str(commit.oid)).serialize_log():
        print(line)
