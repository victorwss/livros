from abc import ABC, abstractmethod
from glob import glob
import os, shutil
from os.path import isfile

def import_dlls() -> None:
    import ctypes
    dll_path = r"C:\Program Files\GTK3-Runtime Win64\bin"
    for dll in ["gobject-2.0-0", "pango-1.0-0", "fontconfig-1", "pangoft2-1.0-0"]:
        ctypes.WinDLL(dll_path + f"\\lib{dll}.dll")

class DirOrFile(ABC):

    def __init__(self, absolute_name: str) -> None:
        n = os.path.abspath(absolute_name).replace("\\", "/")
        self.__absolute_name = n
        self.__local_name = n if "/" not in n else n[n.rindex("/") + 1:]

    @property
    def absolute_name(self) -> str:
        return self.__absolute_name

    @property
    @abstractmethod
    def exists(self) -> bool:
        pass

    @property
    def url(self) -> str:
        return "file:///" + self.absolute_name

    @property
    def local_name(self) -> str:
        return self.__local_name

    def kill(self) -> None:
        pass

class Dir(DirOrFile):

    def files(self, query: str = "*.*") -> list["File"]:
        result: list[File] = []
        for f in glob(f"{self.absolute_name}/{query}"):
            ff = File(f)
            if ff.exists: result.append(ff)
        return result

    @property
    def exists(self) -> bool:
        return os.path.exists(self.absolute_name) and not isfile(self.absolute_name)

    def mkdir(self) -> None:
        if not self.exists: os.mkdir(self.absolute_name)

    def kill(self) -> None:
        if self.exists: shutil.rmtree(self.absolute_name, ignore_errors = True)

    def zip_to(self, target: "File") -> None:
        shutil.make_archive(target.absolute_name, "zip", self.absolute_name)
        os.rename(target.absolute_name + ".zip", target.absolute_name)

    @property
    def single_child_down(self) -> "Dir":
        child = glob(f"{self.absolute_name}/*")
        if len(child) == 1 and not isfile(child[0]): return Dir(child[0]).single_child_down
        return self

    @staticmethod
    def temp() -> "Dir":
        import uuid
        d = Dir(f"temp-{uuid.uuid4()}")
        d.mkdir()
        return d

class File(DirOrFile):

    @property
    def exists(self) -> bool:
        return os.path.exists(self.absolute_name) and isfile(self.absolute_name)

    def save(self, content: str) -> None:
        with open(self.absolute_name, "w", encoding = "utf-8") as f:
            f.write(content)

    def read_as_str(self) -> str:
        with open(self.absolute_name, "r", encoding = "utf-8") as f:
            return f.read()

    def kill(self) -> None:
        if self.exists: os.remove(self.absolute_name)

    def extract_to(self, target: Dir) -> None:
        import zipfile
        with zipfile.ZipFile(self.absolute_name, "r") as zip_ref:
            zip_ref.extractall(target.absolute_name)

    @property
    def local_name_no_extension(self) -> str:
        x = self.local_name
        if "." not in x: return x
        return x[:x.rindex(".")]

    @property
    def extension(self) -> str:
        x = self.local_name
        if "." not in x: return ""
        return x[x.rindex(".") + 1:]

class Biblioteca:

    def __init__(self, src: str) -> None:
        src_file = File(src)
        src_dir = Dir(src)

        if not src_file.exists and not src_dir.exists:
            raise Exception(f"A pasta {src_dir.absolute_name} não existe e o arquivo {src_file.absolute_name} também não.")
        if src_file.exists and src_dir.exists:
            raise Exception(f"A pasta {src_dir.absolute_name} existe e o arquivo {src_file.absolute_name} também. Só pode-se trabalhar com um deles.")

        use_temp_src_dir = src_file.exists

        if use_temp_src_dir:
            if not src.endswith(".zip"):
                raise Exception(f"O arquivo {src_file.absolute_name} não é um arquivo ZIP.")
            src_dir = Dir.temp()
            src_file.extract_to(src_dir)

        self.__use_temp_src_dir = use_temp_src_dir
        self.__src_dir = src_dir
        self.__zip_out = File(f"out-{src}") if src.endswith(".zip") else File(f"out-{src}.zip")

    def assemble(self) -> None:
        print("Iniciando...")
        temp = Dir.temp()
        try:
            src_dir_deep = self.__src_dir.single_child_down
            for f in src_dir_deep.files("*.html"):
                Livro(src_dir_deep, temp, f).assemble()
            print("Zipando tudo...")
            temp.zip_to(self.__zip_out)
        finally:
            print("Limpando...")
            try:
                temp.kill()
            finally:
                if self.__use_temp_src_dir:
                    self.__src_dir.kill()
        print("Fim!")

class Livro:

    def __init__(self, src_dir: Dir, dest_dir: Dir, book_name: File) -> None:
        self.__input = book_name
        self.__temp = File(f"{dest_dir.absolute_name}/{book_name.local_name_no_extension}-temp.html")
        self.__output = File(f"{dest_dir.absolute_name}/{book_name.local_name_no_extension}.pdf")
        self.__src_dir = src_dir

    def assemble(self) -> None:
        html_content1 = self.__render_jinja()
        html_content2 = self.__process_javascript(html_content1)
        self.__html_to_pdf(html_content2)
        print(f"[{self.__output.local_name}] Pronto!")

    # Adaptado de https://stackoverflow.com/a/33944561/540552
    def __render_jinja(self) -> str:
        print(f"[{self.__output.local_name}] Montando o HTML do conteúdo...")
        import jinja2
        return jinja2.Environment(loader = jinja2.FileSystemLoader([self.__src_dir.absolute_name, "plugins"])) \
                .get_template(self.__input.local_name) \
                .render(dir_path = self.__src_dir.url)

    def __html_to_pdf(self, html_content_1: str) -> None:
        print(f"[{self.__output.local_name}] Gerando o PDF do conteúdo...")
        import weasyprint
        weasyprint.HTML(string = html_content_1) \
                .render() \
                .write_pdf(self.__output.absolute_name)

    def __process_javascript(self, html_content_2: str) -> str:
        print(f"[{self.__output.local_name}] Iniciando o Selenium...")
        import time
        from selenium import webdriver
        try:
            self.__temp.save(html_content_2)
            driver = webdriver.Firefox()
            try:
                driver.set_window_size(10, 550)
                print(f"[{self.__output.local_name}] Abrindo a página HTML...")
                driver.get(self.__temp.url)
                print(f"[{self.__output.local_name}] Aguardando o JavaScript...")
                time.sleep(5)
                print(f"[{self.__output.local_name}] Coletando o HTML resultante...")
                e = driver.find_element("xpath", "//*")
                u: str = e.get_attribute("outerHTML") # type: ignore[no-untyped-call]
                return u
            finally:
                driver.quit()
        finally:
            print(f"[{self.__output.local_name}] Limpando o HTML temporário...")
            self.__temp.kill()

def run() -> None:
    import_dlls()
    from sys import argv
    if len(argv) == 2:
        Biblioteca(argv[1]).assemble()
        return

    print("Forma de uso: python livros.py <nome-do-livro>")
    print("Onde <nome-do-livro> é o nome de alguma pasta contendo arquivos HTML junto com CSS, fontes e imagens.")

run()