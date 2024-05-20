import os.path
from pathlib import Path


class AIRepoConstants:
    GIT_AI_ROOT: str = '.git_ai'
    METRICS_FOLDER: str = 'metrics'
    ARTIFACT_FOLDER: str = 'artifacts'
    TENSORBOARD_FOLDER: str = 'tensorboard'
    HPARAMS_JSON: str = 'hparams.json'
    CONFIG_JSON: str = 'config.json'
    TOPOLOGY_FILE: str = 'topology'
    METRICS_PATH = Path(GIT_AI_ROOT) / METRICS_FOLDER
    ARTIFACT_PATH = Path(GIT_AI_ROOT) / ARTIFACT_FOLDER
    HPARAMS_JSON_PATH = Path(GIT_AI_ROOT) / HPARAMS_JSON
    TENSORBOARD_PATH = Path(GIT_AI_ROOT) / TENSORBOARD_FOLDER
    CONFIG_PATH = Path(GIT_AI_ROOT) / CONFIG_JSON
    TOPOLOGY_PATH = Path(GIT_AI_ROOT) / TOPOLOGY_FILE

    def metrics_file_list(self):
        # TODO Check if files exist
        return [self.TENSORBOARD_PATH, self.HPARAMS_JSON_PATH,
                self.METRICS_PATH, self.TOPOLOGY_PATH]

    def filter_ai_repo_files(self, file_list: list[str]) -> list[str]:
        return [
            f for f in file_list if (f.startswith(self.GIT_AI_ROOT))
        ]

    def metric_filename(self, workdir: str, tag: str):
        return os.path.join(workdir, AIRepoConstants.METRICS_PATH,
                            tag)

    def hparam_filename(self, workdir: str):
        return os.path.join(workdir, AIRepoConstants.HPARAMS_JSON_PATH)
