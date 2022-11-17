@echo off
echo.

:parte1
echo 1. Limpando...
del venv /q 2> nul
rd /s /q venv 2> nul

:parte2
echo.
echo 2. Instalando a venv...
python -m venv .\venv

:parte3
echo.
echo 3. Instalando as dependências pelo pip...
.\venv\Scripts\pip install --disable-pip-version-check mypy && ^
.\venv\Scripts\pip install --disable-pip-version-check flask && ^
.\venv\Scripts\pip install --disable-pip-version-check weasyprint && ^
.\venv\Scripts\pip install --disable-pip-version-check selenium && ^
goto parte4
goto fim

:parte4
echo.
echo 4. Verificando o código com o mypy...
.\venv\Scripts\python -m mypy --strict .\src\livros .\src\weasyprint.pyi && ^
goto parte5
goto fim

:parte5
echo.
echo 5. Instalando o pacote executável direto do código-fonte...
robocopy .\src\livros .\venv\Lib\site-packages\livros /E > nul

:parte6
echo.
echo 6. Sucesso!

:fim
echo.
