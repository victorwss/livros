import livros
from livros.model import Biblioteca, File
from livros.server import ServidorLivros
import sys, os
from mypy.util import FancyFormatter

formas_de_uso = """
Formas de uso:
    compilar_livros <nome-do-pacote> [<nome-do-zip>]
    servidor_livros <opções>*

Onde:
* <nome-do-pacote> é o nome de alguma pasta ou arquivo ZIP contendo arquivos HTML junto com CSS, fontes e imagens.
* <nome-do-zip> é o nome do ZIP a ser produzido como resultado. Se omitido, o nome será deduzido a partir do nome do pacote.
* <opções> são as seguintes:
*** [-p <porta>] especifica o número da porta TCP a ser usada no servidor. Se omitido, será utilizada a porta 13013.
*** [-z] especifica, quando presente, que o serviço zelador que apaga arquivos temporários antigos não será ativado.

Exemplo:
    compilar_livros apostila_projeto.zip apostila.zip
    servidor_livros -p 13579 -z"""

class UsoIncorreto(Exception):
    pass

class Cli: # CLI = Command Line Interpreter

    def __compilar(self) -> None:
        if len(sys.argv) == 4:
            biblioteca = Biblioteca(print, False)
            biblioteca.criar_pacote_zip_ou_dir(sys.argv[2], File(sys.argv[3])).assemble()
        elif len(sys.argv) == 3:
            biblioteca = Biblioteca(print, False)
            biblioteca.criar_pacote_zip_ou_dir(sys.argv[2], None).assemble()
        else:
            raise UsoIncorreto()

    def __servidor(self) -> None:

        argvs = 1
        porta = 13013
        if "-p" in sys.argv[1:]:
            idx = sys.argv.index("-p")
            if idx == len(sys.argv) - 1:
                raise UsoIncorreto()
            try:
                porta = int(sys.argv[idx + 1])
            except ValueError as x:
                raise UsoIncorreto()
            argvs += 2

        zelador = True
        if "-z" not in sys.argv[1:]:
            zelador = False
            argvs += 1

        if len(sys.argv) != argvs:
            raise UsoIncorreto()

        biblioteca = Biblioteca(print, zelador)
        ServidorLivros(biblioteca, porta).start()

    def __main(self) -> None:
        try:
            if len(sys.argv) < 2:
                raise UsoIncorreto()
            if sys.argv[1] == "compilar_livros":
                self.__compilar()
            elif sys.argv[1] == "servidor_livros":
                self.__servidor()
            else:
                raise UsoIncorreto()
        except UsoIncorreto as x:
            print(sys.argv)
            print(formas_de_uso)

    # Copiado do __main__.py do mypy.
    def run(self) -> None:
        try:
            self.__main()
            sys.stdout.flush()
            sys.stderr.flush()
        except BrokenPipeError:
            # Python flushes standard streams on exit; redirect remaining output
            # to devnull to avoid another BrokenPipeError at shutdown
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            sys.exit(2)
        except KeyboardInterrupt:
            formatter = FancyFormatter(sys.stdout, sys.stderr, False)
            msg = "Execução interrompida\n"
            sys.stdout.write(formatter.style(msg, color = "red", bold = True))
            sys.stdout.flush()
            sys.stderr.flush()
            sys.exit(2)