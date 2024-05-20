from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Type, Union
from typing_extensions import Self
import json


@dataclass(frozen=True)
class InputRepo:
    path: Path
    uri: str
    commit: str

    def serialize(self) -> dict:
        return {
            'path': list(self.path.parts),
            'uri': self.uri,
            'commit': self.commit
        }

    @classmethod
    def from_dict(cls: Type[Self], d: dict) -> Self:
        path = Path(*d['path'])
        return cls(path=path, uri=d['uri'], commit=d['commit'])


class AIRepoConfig(object):
    def __init__(self) -> None:
        self.is_ai = True
        self.input_repos: dict[Path, InputRepo] = {}

    def add_input_repo(self, input_repo: InputRepo):
        self.input_repos[input_repo.path] = input_repo

    def update_input_repo(self, path: Path, uri: str = "", commit: str = ""):
        old_repo = self.input_repos[path]
        if not uri:
            uri = old_repo.uri

        if not commit:
            commit = old_repo.commit
        self.input_repos[path] = InputRepo(path=path, uri=uri, commit=commit)

    def get_input_repo(self, path: Path) -> Optional[InputRepo]:
        return self.input_repos[path] if path in self.input_repos else None

    @classmethod
    def from_json(cls: Type[Self], j: dict) -> Self:
        new = cls()
        for i in j['input_repos']:
            new.add_input_repo(InputRepo.from_dict(i))
        return new

    @classmethod
    def from_file(cls: Type[Self], file_name: Union[str, Path]) -> Self:
        with open(file_name, 'r') as f:
            j = json.load(f)
        return cls.from_json(j)

    @classmethod
    def from_str(cls: Type[Self], data: bytearray) -> Self:
        new = cls()
        j = json.loads(data)
        return cls.from_json(j)

    @classmethod
    def default(cls: Type[Self]) -> Self:
        return cls()

    def serialize(self):
        return {
            'ai_repo': True,
            'input_repos': [
                i.serialize() for i in self.input_repos.values()
            ]
        }
