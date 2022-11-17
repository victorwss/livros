import livros
from typing import Callable
from abc import ABC, abstractmethod
from glob import glob
import os, shutil, time
from pathlib import PurePath
from threading import RLock
from datetime import datetime, timedelta
from threading import Thread, current_thread

debug_lock = False
debug_zelador = True
descanso_zelador = 60
descanso_javascript = 5
limpeza_preguicosa = False

def log_lock(x: str) -> None:
    if debug_lock: print(x)

def log_zelador(x: str) -> None:
    if debug_zelador: print(x)

class DirOrFile(ABC):

    def __init__(self, absolute_name: str) -> None:
        n = os.path.abspath(absolute_name).replace("\\", "/")
        self.__absolute_name = n
        self.__local_name = n if "/" not in n else n[n.rindex("/") + 1:]

    @property
    def absolute_name(self) -> str:
        return self.__absolute_name

    @property
    def url(self) -> str:
        return "file:///" + self.absolute_name

    @property
    def local_name(self) -> str:
        return self.__local_name

    @abstractmethod
    def kill(self) -> None:
        ...

    @property
    def parent(self) -> "Dir":
        return Dir(PurePath(self.absolute_name).parent.name)

class Dir(DirOrFile):

    def files(self, query: str = "*.*") -> list["File"]:
        result: list[File] = []
        for c in glob(f"{self.absolute_name}/{query}"):
            ff = File(c)
            if ff.exists: result.append(ff)
        return result

    def subdirs(self, query: str = "*") -> list["Dir"]:
        result: list[Dir] = []
        for c in glob(f"{self.absolute_name}/{query}"):
            dd = Dir(c)
            if dd.exists: result.append(dd)
        return result

    @property
    def exists(self) -> bool:
        return os.path.exists(self.absolute_name) and not os.path.isfile(self.absolute_name)

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
        if len(child) == 1 and not os.path.isfile(child[0]): return Dir(child[0]).single_child_down
        return self

    @staticmethod
    def temp() -> "Dir":
        import uuid
        d = Dir(f"temp/{uuid.uuid4()}")
        d.mkdir()
        return d

    def subdir(self, name: str) -> "Dir":
        return Dir(self.absolute_name + "/" + name)

    def file(self, name: str) -> "File":
        return File(self.absolute_name + "/" + name)

class File(DirOrFile):

    @property
    def exists(self) -> bool:
        return os.path.exists(self.absolute_name) and os.path.isfile(self.absolute_name)

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
        with zipfile.ZipFile(self.absolute_name, "r", metadata_encoding = "utf-8") as zf:
            zf.extractall(target.absolute_name)

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

    @staticmethod
    def temp(extensao: str) -> "File":
        import uuid
        f = File(f"temp/{uuid.uuid4()}.{extensao}")
        return f

class UnsavedFile(ABC):

    def __init__(self, local_name: str) -> None:
        self.__local_name = local_name

    @property
    def local_name(self) -> str:
        return self.__local_name

    @abstractmethod
    def save_to(self, d: Dir) -> File:
        ...

class Livro:

    def __init__(self, notify: Callable[[str], None], src_dir: Dir, dest_dir: Dir, book_name: File) -> None:
        self.__input = book_name
        self.__temp = dest_dir.file(f"{book_name.local_name_no_extension}-temp.html")
        self.__output = dest_dir.file(f"{book_name.local_name_no_extension}.pdf")
        self.__src_dir = src_dir
        self.__notify = notify

    def assemble(self) -> None:
        html_content1 = self.__render_jinja()
        html_content2 = self.__process_javascript(html_content1)
        self.__html_to_pdf(html_content2)
        self.__notify(f"[{self.__output.local_name}] Pronto!")

    # Adaptado de https://stackoverflow.com/a/33944561/540552
    def __render_jinja(self) -> str:
        self.__notify(f"[{self.__output.local_name}] Montando o HTML do conteúdo...")
        import jinja2
        plugins = os.path.join(os.path.dirname(__file__), "plugins")
        return jinja2.Environment(loader = jinja2.FileSystemLoader([self.__src_dir.absolute_name, plugins])) \
                .get_template(self.__input.local_name) \
                .render(dir_path = self.__src_dir.url)

    def __html_to_pdf(self, html_content_1: str) -> None:
        self.__notify(f"[{self.__output.local_name}] Gerando o PDF do conteúdo...")
        import weasyprint
        weasyprint.HTML(string = html_content_1) \
                .render() \
                .write_pdf(self.__output.absolute_name)

    def __process_javascript(self, html_content_2: str) -> str:
        self.__notify(f"[{self.__output.local_name}] Iniciando o Selenium...")
        from selenium import webdriver
        try:
            self.__temp.save(html_content_2)
            driver = webdriver.Firefox() # type: ignore[no-untyped-call]
            try:
                self.__notify(f"[{self.__output.local_name}] Abrindo a página HTML...")
                driver.get(self.__temp.url)
                self.__notify(f"[{self.__output.local_name}] Aguardando o JavaScript...")
                time.sleep(descanso_javascript)
                self.__notify(f"[{self.__output.local_name}] Coletando o HTML resultante...")
                e = driver.find_element("xpath", "//*")
                return e.get_attribute("outerHTML")
            finally:
                driver.quit()
        finally:
            if not limpeza_preguicosa:
                self.__notify(f"[{self.__output.local_name}] Limpando o HTML temporário...")
                self.__temp.kill()

class Pacote:

    @staticmethod
    def criar_pacote_zip(notify: Callable[[str], None], src_file: File, dest: File | None) -> "Pacote":
        if not src_file.exists: raise Exception(f"O arquivo {src_file.absolute_name} não existe.")
        if not src_file.local_name.endswith(".zip"): raise Exception(f"O arquivo {src_file.absolute_name} não é um arquivo ZIP.")

        temp_dir = Dir.temp()
        if dest is None: dest = src_file.parent.file(f"out-{src_file.local_name}")
        src_dir = temp_dir.subdir("src")
        src_file.extract_to(src_dir)
        return Pacote(notify, src_dir, dest, temp_dir)

    @staticmethod
    def criar_pacote_dir(notify: Callable[[str], None], src_dir: Dir, dest: File | None) -> "Pacote":
        if not src_dir.exists: raise Exception(f"O diretório {src_dir.absolute_name} não existe.")

        temp_dir = Dir.temp()
        if dest is None: dest = src_dir.parent.file(f"out-{src_dir.local_name}.zip")
        return Pacote(notify, src_dir, dest, temp_dir)

    @staticmethod
    def criar_pacote_unsaved(notify: Callable[[str], None], unsaved: UnsavedFile, dest: File | None) -> "Pacote":
        if not unsaved.local_name.endswith(".zip"): raise Exception(f"O arquivo {unsaved.local_name} não é um arquivo ZIP.")

        temp_dir = Dir.temp()
        if dest is None: dest = temp_dir.file(f"out-{unsaved.local_name}")
        src_file = unsaved.save_to(temp_dir)
        src_dir = temp_dir.subdir("src")
        src_file.extract_to(src_dir)
        return Pacote(notify, src_dir, dest, temp_dir)

    def __init__(self, renotify: Callable[[str], None], src_dir: Dir, dest: File, temp_dir: Dir) -> None:
        self.__temp_dir = temp_dir
        self.__src_dir = src_dir
        self.__zip_out = dest
        self.__renotify = renotify

        self.__lock = RLock()
        self.__status: list[str] = []         # Mutável, guardado pelo lock.
        self.__pronto: datetime | None = None # Mutável, guardado pelo lock.

    def assemble(self) -> None:
        self.__notify("Iniciando...")
        build_dir = self.__temp_dir.subdir("bld")
        try:
            build_dir.mkdir()
            src_dir_deep = self.__src_dir.single_child_down
            for f in src_dir_deep.files("*.html"):
                Livro(self.__notify, src_dir_deep, build_dir, f).assemble()
            self.__notify("Zipando tudo...")
            build_dir.zip_to(self.__zip_out)
        finally:
            if not limpeza_preguicosa:
                self.__notify("Limpando arquivos temporários...")
                build_dir.kill()
                self.__temp_dir.subdir("src").kill()
        self.__notify("Fim!")
        log_lock(f"[lock] {self.nome} (pronto)...")
        with self.__lock:
            log_lock(f"[lock] {self.nome} (pronto) obtido.")
            self.__pronto = datetime.now()

    def limpeza(self) -> bool:
        if not self.old: return False
        log_lock(f"[lock] {self.nome} (limpeza)...")
        with self.__lock:
            log_lock(f"[lock] {self.nome} (limpeza) obtido.")
            self.__temp_dir.kill()
            return True

    def __notify(self, txt: str) -> None:
        log_lock(f"[lock] {self.nome} (notify)...")
        with self.__lock:
            log_lock(f"[lock] {self.nome} (notify) obtido.")
            self.__status.append(txt)
        self.__renotify(f"[{self.__temp_dir.local_name}] {txt}")

    @property
    def status(self) -> list[str]:
        log_lock(f"[lock] {self.nome} (status)...")
        with self.__lock:
            log_lock(f"[lock] {self.nome} (status) obtido.")
            return self.__status[:]

    @property
    def pronto(self) -> datetime | None:
        log_lock(f"[lock] {self.nome} (pronto)...")
        with self.__lock:
            log_lock(f"[lock] {self.nome} (pronto) obtido.")
            return self.__pronto

    @property
    def out_file(self) -> File:
        return self.__zip_out

    @property
    def nome(self) -> str:
        return self.__temp_dir.local_name

    @property
    def old(self) -> bool:
        p = self.pronto
        return p is not None and p - datetime.now() > timedelta(hours = 1)

class Biblioteca:

    def __init__(self, notify: Callable[[str], None], iniciar_zelador: bool) -> None:
        Biblioteca.__import_dlls()
        self.__notify = notify
        self.__lock = RLock()
        self.__pacotes: dict[str, Pacote] = {} # Mutável, guardado pelo lock.
        self.__zelador: Zelador | None = None  # Mutável, guardado pelo lock.

        if iniciar_zelador:
            log_zelador(f"[Zelador] Iniciando o zelador...")
            self.__zelador = Zelador(self.__lock, self.__pacotes)
        else:
            log_zelador(f"[Zelador] Zelador desativado.")

    def criar_pacote_zip_ou_dir(self, src: str, dest: File | None) -> Pacote:
        f = File(src)
        d = Dir(src)
        if not f.exists and not d.exists:
            raise Exception(f"A pasta {d.absolute_name} não existe e o arquivo {f.absolute_name} também não.")
        if f.exists and d.exists:
            raise Exception(f"A pasta {d.absolute_name} existe e o arquivo {f.absolute_name} também. Só pode-se trabalhar com um deles.")
        if f.exists:
            return self.criar_pacote_zip(f, dest)
        return self.criar_pacote_dir(d, dest)

    def criar_pacote_zip(self, src_file: File, dest: File | None) -> Pacote:
        return self.__criar_pacote(lambda: Pacote.criar_pacote_zip(self.__notify, src_file, dest))

    def criar_pacote_dir(self, src_dir: Dir, dest: File | None) -> Pacote:
        return self.__criar_pacote(lambda: Pacote.criar_pacote_dir(self.__notify, src_dir, dest))

    def criar_pacote_unsaved(self, unsaved: UnsavedFile, dest: File | None) -> Pacote:
        return self.__criar_pacote(lambda: Pacote.criar_pacote_unsaved(self.__notify, unsaved, dest))

    def __criar_pacote(self, ctor: Callable[[], Pacote]) -> Pacote:
        log_lock(f"[lock] pacote (criação)...")
        with self.__lock:
            log_lock(f"[lock] pacote (criação) obtido.")
            p = ctor()
            self.__pacotes[p.nome] = p
        return p

    def localizar_pacote(self, arq: str) -> Pacote | None:
        log_lock(f"[lock] pacote (localização)...")
        with self.__lock:
            log_lock(f"[lock] pacote (localização) obtido.")
            return self.__pacotes.get(arq, None)

    @staticmethod
    def __import_dlls() -> None:
        import ctypes
        dll_path = r"C:\Program Files\GTK3-Runtime Win64\bin"
        for dll in ["gobject-2.0-0", "pango-1.0-0", "fontconfig-1", "pangoft2-1.0-0"]:
            ctypes.WinDLL(dll_path + f"\\lib{dll}.dll")

class Zelador:

    def __init__(self, lock: RLock, pacotes: dict[str, Pacote]) -> None:
        self.__lock = lock
        self.__pacotes = pacotes
        executor = Thread(target = self.limpar, args = ())
        executor.daemon = True
        executor.start()

    def limpar(self) -> None:
        while True:
            log_lock(f"[lock] pacote (zelador limpeza)...")
            with self.__lock:
                log_lock(f"[lock] pacote (zelador limpeza) obtido.")
                for k, v in self.__pacotes.items():
                    log_zelador(f"[Zelador] Olhando o pacote {k}")
                    if v.limpeza():
                        log_zelador(f"[Zelador] Eliminado pacote antigo {k}")
                        del self.__pacotes[k]
                for f in Dir("temp").files():
                    log_zelador(f"[Zelador] Olhando o arquivo {f.absolute_name}")
                    if f.local_name != "README.md" and f.local_name not in self.__pacotes:
                        log_zelador(f"[Zelador] Eliminando o arquivo {f.absolute_name}")
                        f.kill()
                for d in Dir("temp").subdirs():
                    log_zelador(f"[Zelador] Olhando o diretório {d.absolute_name}")
                    if d.local_name not in self.__pacotes:
                        log_zelador(f"[Zelador] Eliminando o diretório {d.absolute_name}")
                        d.kill()
            time.sleep(descanso_zelador)