@echo off
echo Iniciando PAPIRE...

:: Verificación de la existencia del entorno virtual
if not exist papire (
    echo El entorno virtual 'papire' no se encuentra. Asegúrate de que el entorno se ha creado.
    pause
    exit /b 1
)

:: Activar entorno virtual
echo Activando entorno virtual...
call papire\Scripts\activate

:: Ejecutar el programa
echo Ejecutando el programa...
python main.py

:: Desactivar el entorno virtual al finalizar
echo Desactivando entorno virtual...
call papire\Scripts\deactivate

echo Programa finalizado.
pause
