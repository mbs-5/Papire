import os
import subprocess
import tempfile
import markdown
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_JUSTIFY
from bs4 import BeautifulSoup
from tkinter import messagebox
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _convert_with_pandoc(input_content, output_file, input_format, output_format):
    """Convierte un archivo usando pandoc."""
    temp_file = None
    try:
        temp_file = tempfile.NamedTemporaryFile(suffix=f".{input_format}", delete=False)
        temp_file.write(input_content.encode('utf-8'))
        temp_file.close()

        subprocess.run(
            ["pandoc", temp_file.name, "-o", output_file, "-t", output_format],
            check=True,
            capture_output=True,
            text=True
        )
        logging.info(f"Archivo convertido con pandoc de {input_format} a {output_format}: {output_file}")

    except FileNotFoundError:
        messagebox.showerror("Error", "Pandoc no está instalado o no se encuentra en el PATH.")
        logging.error("Pandoc no está instalado o no se encuentra en el PATH.")
        raise
    except subprocess.CalledProcessError as e:
         messagebox.showerror("Error", f"Error al convertir con pandoc: {e}\n{e.stderr}")
         logging.error(f"Error al convertir con pandoc: {e}\n{e.stderr}")
         raise
    finally:
         if temp_file:
            os.remove(temp_file.name)

def md_to_html(md_content, output_file):
    """Convierte un contenido Markdown a HTML usando pandoc."""
    try:
      _convert_with_pandoc(md_content, output_file, "md", "html")
    except Exception as e:
        messagebox.showerror("Error", "Error al convertir a HTML con pandoc.")
        logging.error(f"Error al convertir a HTML con pandoc: {e}")

def md_to_docx(md_content, output_file):
     """Convierte un contenido Markdown a DOCX usando pandoc."""
     try:
        _convert_with_pandoc(md_content, output_file, "md", "docx")
     except Exception as e:
        messagebox.showerror("Error", "Error al convertir a DOCX con pandoc.")
        logging.error(f"Error al convertir a DOCX con pandoc: {e}")

def md_to_latex(md_content, output_file):
    """Convierte un contenido Markdown a LaTeX usando pandoc."""
    try:
        _convert_with_pandoc(md_content, output_file, "md", "latex")
    except Exception as e:
        messagebox.showerror("Error", "Error al convertir a LaTeX con pandoc.")
        logging.error(f"Error al convertir a LaTeX con pandoc: {e}")

def md_to_pdf(md_content, output_file):
    """Convierte un contenido Markdown a PDF usando ReportLab."""
    try:
        # Convertir Markdown a HTML
        html_content = markdown.markdown(md_content)

        # Crear un objeto DocumentTemplate
        doc = SimpleDocTemplate(output_file, pagesize=letter)
        styles = getSampleStyleSheet()
        style = styles["Normal"]
        style.alignment = TA_JUSTIFY
        # Crear una lista para elementos
        story = []

        # Crear un objeto Paragraph con el contenido HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        for element in soup.recursiveChildGenerator():
            if isinstance(element, str):
                if element.strip():
                  p = Paragraph(str(element), style)
                  story.append(p)
            elif element.name in ["h1","h2","h3","h4","h5","h6", "b", "strong", "i", "em"]:
                p = Paragraph(str(element), styles["Normal"])
                story.append(p)

        doc.build(story)
        logging.info(f"Archivo PDF creado con ReportLab: {output_file}")
    except Exception as e:
        messagebox.showerror("Error", f"Error al convertir a PDF con ReportLab: {e}")
        logging.error(f"Error al convertir a PDF con ReportLab: {e}")

def md_to_epub(md_content, output_file):
    """Convierte un contenido Markdown a EPUB usando pandoc."""
    try:
        _convert_with_pandoc(md_content, output_file, "md", "epub")
    except Exception as e:
        messagebox.showerror("Error", "Error al convertir a EPUB con pandoc.")
        logging.error(f"Error al convertir a EPUB con pandoc: {e}")


def html_to_pdf(html_content, output_file):
    """Convierte un contenido HTML a PDF usando pandoc."""
    try:
       _convert_with_pandoc(html_content,output_file, "html", "pdf")
    except Exception as e:
        messagebox.showerror("Error", "Error al convertir a PDF con pandoc.")
        logging.error(f"Error al convertir a PDF con pandoc: {e}")

def html_to_epub(html_content, output_file):
     """Convierte un contenido HTML a EPUB usando pandoc."""
     try:
         _convert_with_pandoc(html_content, output_file, "html", "epub")
     except Exception as e:
        messagebox.showerror("Error", "Error al convertir a EPUB con pandoc.")
        logging.error(f"Error al convertir a EPUB con pandoc: {e}")

def html_to_mobi(html_content,output_file):
    """Convierte un contenido HTML a MOBI usando pandoc."""
    try:
         _convert_with_pandoc(html_content,output_file,"html", "mobi")
    except Exception as e:
        messagebox.showerror("Error", "Error al convertir a MOBI con pandoc.")
        logging.error(f"Error al convertir a MOBI con pandoc: {e}")

def convert_file(content, output_file, format):
    if format == "Markdown":
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(content)
    elif format == "HTML":
       md_to_html(content, output_file)
    elif format == "DOCX":
        md_to_docx(content, output_file)
    elif format == "Latex":
        md_to_latex(content, output_file)
    elif format == "PDF":
        md_to_pdf(content, output_file)
    elif format == "EPUB":
        md_to_epub(content, output_file)
    elif format == "txt":
         with open(output_file, 'w', encoding='utf-8') as file:
            file.write(content)
    logging.info(f"Archivo guardado en formato {format}: {output_file}")