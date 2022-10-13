from typing import Any, List, Sequence, Tuple

Tree = Tuple[str, Tuple[int, float, float], Sequence[Any], Any]

class Page:
    pass

class Document:
    def write_pdf(self, s: str) -> None: ...

    @property
    def pages(self) -> List[Page]: ...

    def make_bookmark_tree(self) -> Sequence[Tree]: ...

class Html:
    def render(self) -> Document: ...

def HTML(string: str) -> Html: ...