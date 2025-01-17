import os
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_base_filename(file_path):
    """
     Obtiene el nombre base de un archivo sin la extensión.
    """
    try:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        logging.debug(f"Obtenido el nombre base del archivo: {base_name} desde {file_path}")
        return base_name
    except Exception as e:
      logging.error(f"Error obteniendo el nombre base del archivo desde {file_path}: {e}")
      return None