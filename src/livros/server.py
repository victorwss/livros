import livros
from livros.model import Biblioteca, Dir, File, UnsavedFile
from flask import Flask, jsonify, redirect, request, render_template, send_file, url_for
from werkzeug.wrappers.response import Response
from werkzeug.exceptions import BadRequest, NotFound
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from threading import Thread

class ServerUnsavedFile(UnsavedFile):

    def __init__(self, arquivo: FileStorage) -> None:
        if arquivo.filename is None: raise BadRequest()
        super().__init__(secure_filename(arquivo.filename))
        self.__arquivo = arquivo

    def save_to(self, d: Dir) -> File:
        f = d.file(self.local_name)
        self.__arquivo.save(f.absolute_name)
        return f

class ServidorLivros:

    def __init__(self, biblioteca: Biblioteca, port: int = 13013) -> None:
        self.__app = Flask(__name__)
        self.__biblioteca = biblioteca
        self.__port = port

        app = self.__app

        @app.get("/")
        def index() -> str:
            return render_template("tela-upload.html")

        @app.post("/compilar")
        def upload() -> Response:
            if "zip" not in request.files: raise BadRequest()
            arquivo = request.files["zip"]
            f = ServerUnsavedFile(arquivo)
            p = biblioteca.criar_pacote_unsaved(f, None)
            r = redirect(url_for("tela_espera", arq = p.nome))
            t = Thread(target = p.assemble, args = ())
            t.start()
            return r

        @app.get("/<arq>/espera")
        def tela_espera(arq: str) -> str:
            return render_template("tela-status.html", codigo = arq)

        @app.get("/<arq>/status")
        def status(arq: str) -> tuple[Response, int]:
            p = biblioteca.localizar_pacote(arq)
            if p is None: raise NotFound()
            return jsonify(p.status), 201 if p.pronto else 202

        @app.get("/<arq>")
        def download(arq: str) -> tuple[Response, int]:
            p = biblioteca.localizar_pacote(arq)
            if p is None: raise NotFound()
            t = send_file(p.out_file.absolute_name)
            return t, 200

    def start(self) -> None:
        def run() -> None:
            self.__app.run(port = self.__port, host = "0.0.0.0")
        t = Thread(target = run, args = ())
        t.start()