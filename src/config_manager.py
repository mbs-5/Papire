import json
import os
from tkinter import messagebox
import openai
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_FILE = "config.json"
DEFAULT_MAX_TOKENS = 16000
DEFAULT_USE_MAX_TOKENS = False
DEFAULT_LLM_MODEL = "gpt-4o-mini"
DEFAULT_LLMS_FILE = "assets/llms/openai.txt"
DEFAULT_PROMPTS_DIR = "assets/prompts/"
DEFAULT_OUTPUT_DIR = "outputs"
DEFAULT_OUTPUT_FORMATS = ["Markdown"]
DEFAULT_LANGUAGE = "español"


def load_config():
    """Carga la configuración desde el archivo JSON o crea una por defecto."""
    try:
        with open(CONFIG_FILE, 'r') as file:
            config = json.load(file)
        logging.info(f"Configuración cargada desde {CONFIG_FILE}")
    except (FileNotFoundError, json.JSONDecodeError):
        config = {
            'llms_file': DEFAULT_LLMS_FILE,
            'prompts_dir': DEFAULT_PROMPTS_DIR,
            'output_dir': DEFAULT_OUTPUT_DIR,
            'max_tokens': DEFAULT_MAX_TOKENS,
            'use_max_tokens': DEFAULT_USE_MAX_TOKENS,
            'api_key': "",
            'output_formats': DEFAULT_OUTPUT_FORMATS,
            'language': DEFAULT_LANGUAGE
        }
        save_config(config) #Guarda la configuración por defecto
        logging.warning(f"No se encontró la configuración, creando una por defecto y guardando en {CONFIG_FILE}")
    
    _validate_config(config)
    return config

def save_config(config):
    """Guarda la configuración en el archivo JSON."""
    try:
        with open(CONFIG_FILE, 'w') as file:
            json.dump(config, file, indent=4)
        logging.info(f"Configuración guardada en {CONFIG_FILE}")
    except Exception as e:
        messagebox.showerror("Error", f"Error al guardar la configuración: {e}")
        logging.error(f"Error al guardar la configuración: {e}")

def _validate_config(config):
    """Valida la configuración cargada."""
    if not os.path.exists(config['llms_file']):
       logging.warning(f"El archivo de modelos LLM no existe en {config['llms_file']}, usando {DEFAULT_LLMS_FILE}")
       config['llms_file'] = DEFAULT_LLMS_FILE

    if not os.path.exists(config['prompts_dir']):
       logging.warning(f"El directorio de prompts no existe en {config['prompts_dir']}, usando {DEFAULT_PROMPTS_DIR}")
       config['prompts_dir'] = DEFAULT_PROMPTS_DIR

    if not config.get('output_dir'):
        logging.warning(f"No se encuentra el directorio de outputs, usando {DEFAULT_OUTPUT_DIR}")
        config['output_dir'] = DEFAULT_OUTPUT_DIR
    if not config.get('max_tokens'):
        logging.warning(f"No se encuentran los tokens maximos, usando {DEFAULT_MAX_TOKENS}")
        config['max_tokens'] = DEFAULT_MAX_TOKENS
    if not config.get('use_max_tokens') is not None:  # <- Validación de use_max_tokens
        logging.warning(f"No se encuentra la config de usar maximos tokens, usando {DEFAULT_USE_MAX_TOKENS}")
        config['use_max_tokens'] = DEFAULT_USE_MAX_TOKENS
    if not config.get('language'):
        logging.warning(f"No se encuentra el idioma, usando {DEFAULT_LANGUAGE}")
        config['language'] = DEFAULT_LANGUAGE

def load_llm_list(config):
    """Carga la lista de modelos LLM desde un archivo."""
    llm_file = config.get('llms_file', DEFAULT_LLMS_FILE)
    try:
        with open(llm_file, 'r') as file:
            llm_list = file.read().strip().split(',')
        logging.info(f"Lista de modelos LLM cargada desde {llm_file}")
        return llm_list
    except FileNotFoundError:
        logging.error(f"No se encontró el archivo de modelos LLM en {llm_file}")
        return []

def load_prompts(config, language):
    """Carga los prompts desde un directorio específico del idioma."""
    prompt_dir = os.path.join(config.get('prompts_dir', DEFAULT_PROMPTS_DIR), language)
    try:
        prompts = {}
        for filename in os.listdir(prompt_dir):
            if filename.endswith(".txt"):
                filepath = os.path.join(prompt_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as file:
                    prompts[filename[:-4]] = file.read()
        logging.info(f"Prompts cargados desde {prompt_dir}")
        return prompts
    except FileNotFoundError:
        logging.error(f"No se encontró el directorio de prompts en {prompt_dir}")
        return {}
    
def validate_api_key(config):
    """Valida la API key de OpenAI."""
    api_key = config.get('api_key')
    if not api_key:
        logging.warning("API key no configurada.")
        return False
    try:
        openai.api_key = api_key
        openai.models.list()
        logging.info("API key validada correctamente.")
        return True
    except Exception as e:
        messagebox.showerror("Error", f"Error al validar la API key: {e}")
        logging.error(f"Error al validar la API key: {e}")
        return False