import fitz
from tkinter import messagebox, simpledialog
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_texts_by_chapter(doc, toc):
    """Extrae el texto de un PDF por capítulo."""
    texts_by_chapter = {}
    if not toc:
        manual_chapters = simpledialog.askstring("Introducir intervalos de página", "Introduce los intervalos de páginas separados por comas (ej: 1-10,15-20)", parent=None)
        if not manual_chapters:
            logging.warning("Extracción de capítulos cancelada por el usuario.")
            return texts_by_chapter #Si el usuario cancela la operación, cancela tambien el resto

        try:
            for chapter_range in manual_chapters.split(','):
                start, end = map(int, chapter_range.split('-'))
                titulo = f"Páginas {start}-{end}"
                texto_capitulo = ""
                for page_num in range(start - 1, end):
                    page = doc[page_num]
                    texto_capitulo += page.get_text()
                texts_by_chapter[titulo] = texto_capitulo
            logging.info("Textos de capítulos extraídos manualmente.")
        except ValueError:
            messagebox.showerror("Error", "Formato de intervalos incorrecto. Debe ser algo así: 1-10,15-20")
            logging.error("Formato de intervalos manual incorrecto.")
        
        return texts_by_chapter

    for i, (_, title, page) in enumerate(toc):
        chapter_start = page - 1
        
        next_chapter = next((ch for ch in toc[i+1:] if ch[0] <= toc[i][0]), None)
        chapter_end = next_chapter[2] - 2 if next_chapter else doc.page_count - 1

        if chapter_start > chapter_end:
             continue
        
        texto_capitulo = ""
        for page_num in range(chapter_start, chapter_end + 1):
            page = doc[page_num]
            texto_capitulo += page.get_text()

        texts_by_chapter[title] = texto_capitulo
    logging.info("Textos de capítulos extraídos del índice del PDF.")
    return texts_by_chapter


def extract_full_text(doc):
    """Extrae el texto completo de un documento PDF."""
    full_text = ""
    for page_num in range(doc.page_count):
        page = doc[page_num]
        full_text += page.get_text()
    logging.info("Texto completo extraído del PDF.")
    return full_text

def verify_text_extraction(doc, extracted_text):
    """Verifica si se extrajo correctamente el texto del PDF."""
    if not extracted_text.strip():
        messagebox.showwarning("Advertencia", "No se pudo extraer texto del PDF. Asegúrate de que el PDF no sea una imagen escaneada sin capa de texto")
        logging.warning("No se pudo extraer texto del PDF.")
        return False
    logging.info("Verificación de extracción de texto exitosa.")
    return True