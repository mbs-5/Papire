@echo off
echo Iniciando la instalación...

:: Descargar e instalar Python (si no está instalado)
echo Verificando si Python está instalado...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python no encontrado. Iniciando descarga...
    bitsadmin /transfer "PythonInstaller" https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe "%TEMP%\python-3.12.7-amd64.exe"
    
    echo Instalando Python...
    start /wait "" "%TEMP%\python-3.12.7-amd64.exe" /quiet InstallAllUsers=1 Include_launcher=1 Shortcuts=1  
    
    echo Python instalado con éxito.
    
) else (
    echo Python ya está instalado.
)

:: Crear entorno virtual 'papire'
echo Creando entorno virtual 'papire'...
python -m venv papire

:: Activar entorno virtual
echo Activando entorno virtual...
call papire\Scripts\activate

:: Instalar/Actualizar pip
echo Asegurando que pip está actualizado...
python -m pip install --upgrade pip

:: Instalar dependencias de Python
echo Instalando dependencias de Python...
python -m pip install -r requirements.txt
echo Dependencias de Python instaladas con éxito.

:: Descargar e instalar Pandoc (si no está instalado)
echo Verificando si Pandoc está instalado...
where pandoc >nul 2>&1
if %errorlevel% neq 0 (
    echo Pandoc no encontrado. Iniciando descarga e instalación...
    
    bitsadmin /transfer "PandocInstaller" https://github.com/jgm/pandoc/releases/download/3.3/pandoc-3.3-windows-x86_64.msi "%TEMP%\pandoc-3.3-windows-x86_64.msi"
    
    echo Instalando Pandoc...
    start /wait "" "%TEMP%\pandoc-3.3-windows-x86_64.msi" /quiet
    
    echo Pandoc instalado con éxito.

) else (
    echo Pandoc ya está instalado.
)

echo Instalación completa.
pause