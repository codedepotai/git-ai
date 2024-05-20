import json
from typing import Union
from pygit2 import Repository, Oid
from git_ai.cmd.constants import AIRepoConstants

from git_ai.test.utils.data_gen import Metric, Plot


class AIRepoRead:
    def __init__(self, handle: Repository) -> None:
        self.repo = handle

    def get_experiments(self) -> list[str]:
        return [
            b.removeprefix("origin/").removeprefix("exp/")
            for b in self.repo.branches if "exp/" in b
        ]

    def get_metrics(self, exp="", data_commit: Union[str, Oid] = "") -> dict[str, Metric]:
        if exp:
            commit_oid = self.repo.branches["exp/%s" % exp].target
        else:
            commit_oid = data_commit

        commit = self.repo.get(commit_oid)
        blob = commit.tree / AIRepoConstants.HPARAMS_JSON_PATH    # type: ignore
        metrics_json = json.loads(blob.data)
        return {m['label']: Metric.from_json(m) for m in metrics_json}

    def get_plots(self, exp="", data_commit: Union[str, Oid] = "") -> dict[str, Plot]:
        if exp:
            commit_oid = self.repo.branches["exp/%s" % exp].target
        else:
            commit_oid = data_commit
        commit = self.repo.get(commit_oid)
        plots_folder = commit.tree / AIRepoConstants.METRICS_PATH    # type: ignore
        return {
            f.name.removesuffix('_header'):
            Plot.from_json(
                json.loads(f.data),
                json.loads(plots_folder[f.name.removesuffix('_header')].data))
            for f in plots_folder if f.name.endswith('_header')}
