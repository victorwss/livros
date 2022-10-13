from typing import Tuple

class Image:
    @staticmethod
    def open(name: str) -> 'Image': ...

    @property
    def size(self) -> Tuple[int, int]: ...