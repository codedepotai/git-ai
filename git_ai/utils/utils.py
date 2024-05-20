import os
from pathlib import Path
from typing import Union


def list_path(path: Union[str, Path]) -> list[Union[str, Path]]:
    if os.path.isfile(path):
        return [path]
    else:
        f = []
        for (dirpath, _, filenames) in os.walk(path):
            f.extend([os.path.join(dirpath, f) for f in filenames])

        return f
