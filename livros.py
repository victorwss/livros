import os
import jinja2
import json
import time
from sys import argv
from selenium import webdriver
from weasyprint import HTML, Document
from typing import Any, Dict, Tuple, TYPE_CHECKING

def emoji_map(json_content: str, dir_path: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    j1 = json.loads(json_content)
    j2 = {}
    j3 = {}
    for k in j1:
        r = j1[k].replace("{{dir_path}}", dir_path)
        j2[k] = r
        j3[k] = f'<span class="emoji" style="background-image: url({r});">{k}</span>'
    return (j2, j3)

# Obtido de https://stackoverflow.com/a/33944561/540552
def render_jinja(file_name: str, template_loc: str, **context: Any) -> str:
    loader = jinja2.FileSystemLoader(template_loc + "/")
    return jinja2.Environment(loader = loader).get_template(file_name).render(context)

def save_str_to_file(content: str, file_name: str) -> None:
    with open(file_name, 'w', encoding = "utf-8") as f:
        f.write(content)

def read_str_from_file(file_name: str) -> str:
    with open(file_name, encoding = "utf-8") as f:
        return f.read()

def assemble_book(book_name: str) -> None:
    if not os.path.exists(book_name):
        print(f"Não existe a pasta {book_name}.")
        return

    dir_path_naked: str = os.path.abspath(book_name).replace("\\", "/")
    dir_path: str = "file:///" + dir_path_naked
    html_file: str = book_name + ".html"
    output_file: str = book_name + ".pdf"

    print("Lendo emojis...")
    try:
        json_emojis = read_str_from_file(dir_path_naked + "/emojis.json")
    except FileNotFoundError as e:
        json_emojis = "{}"
    emojis: Tuple[Dict[str, str], Dict[str, str]] = emoji_map(json_emojis, dir_path)

    print("Montando o HTML do conteúdo...")
    html_content: str = render_jinja(
        html_file, \
        template_loc = dir_path_naked, \
        dir_path = dir_path, \
        emoji = emojis[1], \
        emoji_src = emojis[0]
    )

    for emoji in emojis[1]:
        html_content = html_content.replace(emoji, emojis[1][emoji])

    html_content = process_javascript(html_content, dir_path_naked, dir_path)

    print("Gerando o PDF do conteúdo...")
    doc_conteudo: Document = HTML(string = html_content).render()
    doc_conteudo.write_pdf(output_file)

    print("Pronto!")

def process_javascript(html_content, dir_path_naked, dir_path):
    save_str_to_file(html_content, dir_path_naked + "/temp-temp-temp.html")
    driver = webdriver.Firefox()
    driver.set_window_size(10, 550)
    driver.get(dir_path + "/temp-temp-temp.html")
    time.sleep(5)
    src = driver.find_element("xpath", "//*").get_attribute("outerHTML")
    driver.quit()
    return src

def run() -> None:
    if len(argv) == 2:
        assemble_book(argv[1])
        return

    print("Forma de uso: python livros.py <nome-do-livro>")
    print("Onde <nome-do-livro> é o nome de alguma pasta contendo arquivos HTML junto com CSS, fontes e imagens.")

run()