from typing import Any, Sequence

Tree = tuple[str, tuple[int, float, float], Sequence[Any], Any]

class Page:
    pass

class Document:
    def write_pdf(self, s: str) -> None: ...

    @property
    def pages(self) -> list[Page]: ...

    def make_bookmark_tree(self) -> Sequence[Tree]: ...

class Html:
    def render(self) -> Document: ...

def HTML(string: str) -> Html: ...