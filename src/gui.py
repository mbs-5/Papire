import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
from PIL import Image, ImageTk
import fitz
import logging
from src import config_manager, pdf_handler, openai_handler, file_converter, utils
import openai
import json

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

format_ext = {"Markdown": ".md", "Latex": ".tex", "PDF": ".pdf", "EPUB": ".epub", "DOCX": ".docx", "HTML": ".html", "txt": ".txt"}
# Initialize global state
state = {
    "pdf_path": "",
    "prompt_path": "",
    "llm_model": "",
    "selected_chapters": {},
    "chapter_checkbuttons": {},
    "settings_window": None,
    "config": None,
    "prompts": {},
    "llm_list": [],
    "language": "español",
    "translations": {},
    "language_combobox": None, # Para el combobox de idioma
}
root = None

def load_translations(language):
    """Carga las traducciones del idioma especificado."""
    try:
        lang_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "lang")       
        # Buscar archivos .json en el directorio de idiomas
        available_languages = [f.replace(".json", "") for f in os.listdir(lang_dir) if f.endswith(".json")]
        if language not in available_languages:
            language = 'es' # Establecer un idioma por defecto si no se encuentra el especificado
        lang_file = os.path.join(lang_dir, f"{language}.json")
        logging.info(f"Intentando cargar traducciones desde: {lang_file}") # Agrega este log
        with open(lang_file, 'r', encoding='utf-8') as file:
            state["translations"] = json.load(file)
        logging.info(f"Traducciones cargadas exitosamente desde {lang_file}")
    except FileNotFoundError:
        logging.error(f"No se encontró el archivo de traducciones para el idioma: {language}")
        state["translations"] = {}
    except json.JSONDecodeError:
        logging.error(f"Error al decodificar el archivo JSON para el idioma: {language}")
        state["translations"] = {}

def translate(key):
    """Obtiene la traducción para la clave dada o devuelve la clave si no se encuentra."""
    translation = state["translations"].get(key, key)
    if translation == key:
      logging.warning(f"Clave de traducción no encontrada: {key}") # Agrega este log
    return translation

def create_button_with_label(parent, text_key, command, row, col, label_key=""):
     """Crea un botón con una etiqueta asociada y devuelve ambos."""
     button = ttk.Button(parent, text=translate(text_key), command=command)
     button.grid(row=row, column=col, sticky="w", padx=5, pady=5)
     label = ttk.Label(parent, text=translate(label_key))
     label.grid(row=row, column=col + 1, sticky="ew", padx=5, pady=5)
     return button, label

def select_pdf():
    """Abre un diálogo para seleccionar un archivo PDF."""
    state["pdf_path"] = filedialog.askopenfilename(title=translate("Seleccionar archivo PDF"), filetypes=[("Archivos PDF", "*.pdf")])
    pdf_label.config(text=f"{translate('PDF')}: {os.path.basename(state['pdf_path'])}" if state["pdf_path"] else f"{translate('PDF')}: {translate('Ninguno seleccionado')}")
    
    if state["pdf_path"]:
         chapter_frame.grid() #muestra el frame con los capitulos
         state["chapter_checkbuttons"] = {} #vacía el dict de checkbuttons
         state["selected_chapters"] = {} #vacía el dict de seleccion de capitulos
         update_chapter_list()#Actualiza la lista de capitulos si se elige un nuevo pdf

def select_prompt():
    """Selecciona un prompt del combobox y actualiza la etiqueta."""
    prompt_seleccionado = prompt_combobox.get()
    if prompt_seleccionado:
        state["prompt_path"] = os.path.join(state["config"]["prompts_dir"],state["language"], prompt_seleccionado + ".txt")
        prompt_label.config(text=f"{translate('Prompt')}: {prompt_seleccionado}")
        state["config"]['last_prompt'] = prompt_seleccionado  # Guardar el prompt seleccionado
        config_manager.save_config(state["config"])
    else:
        prompt_label.config(text=f"{translate('Prompt')}: {translate('Ninguno seleccionado')}")
        
def select_llm():
     """Selecciona un modelo LLM del combobox y actualiza la etiqueta."""
     state["llm_model"] = llm_combobox.get()
     llm_label.config(text=f"LLM: {state['llm_model']}" if state["llm_model"] else f"LLM: {translate('Ninguno seleccionado')}")

def process_pdf():
    """Procesa el PDF seleccionado."""
    if not all([state["pdf_path"], state["prompt_path"], state["llm_model"]]):
        messagebox.showerror("Error", translate("Por favor, seleccione PDF, prompt y modelo LLM."))
        return

    if not state["config"].get("api_key"):
        messagebox.showerror("Error", translate("Por favor, configure su API key en el menú de configuración."))
        return
    
    if not config_manager.validate_api_key(state["config"]):
         return

    if not state["llm_list"]:
        messagebox.showerror("Error", translate("No se encontraron modelos LLM válidos en el archivo especificado. Por favor, configúrelo en el menú de configuración."))
        return

    if not state["prompts"]:
        messagebox.showerror("Error", translate("No se encontraron prompts válidos en el directorio especificado. Por favor, configúrelo en el menú de configuración."))
        return

    openai.api_key = state["config"].get("api_key")
    max_tokens = int(state["config"].get("max_tokens"))
    
    # Usar threading para evitar el bloqueo de la interfaz
    threading.Thread(target=_process_pdf_thread, daemon=True).start()

def _process_pdf_thread():
    try:
        progress_bar.grid()
        progress_label.config(text=translate("Cargando PDF..."))
        root.update()

        doc = fitz.open(state["pdf_path"])
        toc = doc.get_toc()

        if not toc:
            messagebox.showwarning(translate("Atención"), translate("No se detectó un índice en el PDF. Introduzca los intervalos manualmente"))
            textos_por_capitulo = pdf_handler.extract_texts_by_chapter(fitz.open(state["pdf_path"]), [])
        else:
            textos_por_capitulo = pdf_handler.extract_texts_by_chapter(doc, toc)

        prompt_seleccionado = state["prompts"].get(os.path.basename(state["prompt_path"])[:-4])

        max_tokens = int(state["config"].get("max_tokens"))
        
        resultados_resumenes = []
        chapter_count = len(textos_por_capitulo)
        progress_bar['maximum'] = chapter_count
        progress_bar['value'] = 0
        progress_label.config(text=translate("Resumiendo capítulos..."))
        root.update()
      
        for index, (titulo_capitulo, texto_capitulo) in enumerate(textos_por_capitulo.items()):
            if state["selected_chapters"].get(titulo_capitulo, True):
                resumen_capitulo = ""
                if state["config"].get("use_max_tokens",True): # Usar max_tokens si el checkbutton está activado
                    partes_texto = openai_handler.split_text(texto_capitulo, max_tokens * 2)
                    for parte in partes_texto:
                        respuesta_openai = openai_handler.summarize_with_openai(state["llm_model"], prompt_seleccionado, parte, max_tokens)
                        resumen_capitulo += respuesta_openai + "\n"
                else:  # No usar max_tokens
                    respuesta_openai = openai_handler.summarize_with_openai(state["llm_model"], prompt_seleccionado, texto_capitulo)
                    resumen_capitulo = respuesta_openai + "\n"

                resultados_resumenes.append(f"## {titulo_capitulo}\n{resumen_capitulo}\n")
            progress_bar['value'] = index + 1
            # Actualizar el color de la barra y forzar una actualización visual
            progress_bar.configure(style='green.Horizontal.TProgressbar')
            progress_bar.update()

        progress_label.config(text=translate("Guardando resultados..."))
        root.update()

        resultado_final = "\n".join(resultados_resumenes)
        save_result(resultado_final)
        doc.close()
        progress_bar.grid_remove()
        progress_label.config(text="")

    except Exception as e:
        messagebox.showerror("Error", f"{translate('Error al procesar el PDF')}: {e}")
        logging.error(f"Error al procesar el PDF: {e}")
        progress_bar.grid_remove()
        progress_label.config(text="")

def save_result(resultado):
    """Guarda el resultado en los formatos seleccionados."""
    if not state["pdf_path"]:
        messagebox.showerror("Error", translate("Debes elegir un pdf primero"))
        return

    base_name = os.path.splitext(os.path.basename(state["pdf_path"]))[0]
    output_base_dir = state["config"].get("output_dir", "outputs")
    output_dir = os.path.join(output_base_dir, base_name) 
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_file_base = os.path.join(output_dir, base_name)

    for format_name in state["config"].get("output_formats", ["Markdown"]):
        try:
            output_file = f"{output_file_base}{format_ext.get(format_name,'.txt')}"
            file_converter.convert_file(resultado,output_file, format_name)
        except Exception as e:
            messagebox.showerror("Error", f"{translate('Error al guardar el archivo en formato')} {format_name}: {e}")
            logging.error(f"Error al guardar el archivo en formato {format_name}: {e}")

    messagebox.showinfo(translate("Éxito"), f"{translate('Archivos guardados en')}: {output_dir}")

def update_chapter_list():
    """Actualiza la lista de capítulos en la interfaz."""
    if not state["pdf_path"]:
         return
    try:
        doc = fitz.open(state["pdf_path"])
        toc = doc.get_toc()
        
        if not toc:
            messagebox.showwarning(translate("Atención"), translate("No se detectó un índice en el PDF."))
            return
        
        for widget in chapter_frame.winfo_children():
            widget.destroy()  # Clear existing widgets
        
        # Crear Canvas y Scrollbar
        canvas = tk.Canvas(chapter_frame)
        scrollbar = ttk.Scrollbar(chapter_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        # Añadir el evento del scroll del ratón
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1*(event.delta/120)), "units"))

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        chapter_frame.grid_rowconfigure(0, weight=1)
        chapter_frame.grid_columnconfigure(0, weight=1)
        
        # Checkbutton para seleccionar/deseleccionar todos los capítulos
        all_selected = tk.BooleanVar(value=True)
        
        def toggle_all():
            for chapter, var in state["chapter_checkbuttons"].items():
                var.set(all_selected.get())
                state["selected_chapters"][chapter] = all_selected.get()

        check_all = ttk.Checkbutton(scrollable_frame, text=translate("Seleccionar Todos"), variable=all_selected, command=toggle_all)
        check_all.grid(row=0, column=0, sticky='w', padx=5, pady=5)
        
        for index, (_, titulo_capitulo, _) in enumerate(toc):
            chapter_var = tk.BooleanVar(value=state["selected_chapters"].get(titulo_capitulo, True))

            def update_selection(title, var):
                state["selected_chapters"][title] = var.get()

            checkbutton = ttk.Checkbutton(scrollable_frame, text=titulo_capitulo, variable=chapter_var,
                                       command=lambda title=titulo_capitulo, var=chapter_var: update_selection(title, var))
            checkbutton.grid(row=index + 1, column=0, sticky='w', padx=5, pady=2)
            state["chapter_checkbuttons"][titulo_capitulo] = chapter_var
        doc.close()

    except Exception as e:
        messagebox.showerror("Error", f"{translate('Error al obtener la lista de capítulos')}: {e}")
        logging.error(f"Error al obtener la lista de capítulos: {e}")

def open_settings():
    if state["settings_window"] and state["settings_window"].winfo_exists():
        state["settings_window"].lift()  # Bring the window to the front if it exists
        return

    state["settings_window"] = tk.Toplevel(root)
    state["settings_window"].title(translate("Configuración"))
    state["settings_window"].geometry("500x250")  # Aumentar la altura para el nuevo botón
    state["settings_window"].resizable(False, False)
    state["settings_window"].protocol("WM_DELETE_WINDOW", lambda: state["settings_window"].destroy())
    state["settings_window"].transient(root)
    state["settings_window"].attributes('-toolwindow', True)  # Remove minimize and maximize buttons

    settings_frame = ttk.Frame(state["settings_window"], padding=10)
    settings_frame.pack(fill="both", expand=True)

    # --- API Key ---
    ttk.Label(settings_frame, text=translate("API Key de OpenAI:")).grid(row=0, column=0, sticky="w", padx=5, pady=5)
    api_key_var = tk.StringVar(value=state["config"].get("api_key", ""))
    api_key_entry = ttk.Entry(settings_frame, textvariable=api_key_var, show="*")
    api_key_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
    settings_frame.columnconfigure(1, weight=1)

    # --- Output Directory ---
    ttk.Label(settings_frame, text=translate("Directorio de Salida:")).grid(row=1, column=0, sticky="w", padx=5, pady=5)
    output_dir_var = tk.StringVar(value=state["config"].get("output_dir", ""))
    output_dir_label = ttk.Label(settings_frame, text=os.path.basename(output_dir_var.get()) if output_dir_var.get() else translate("Por defecto"))
    output_dir_label.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

    def select_output_dir():
        state["settings_window"].lift()  # Ensure the settings window is always in front
        output_dir = filedialog.askdirectory(title=translate("Seleccionar directorio de salida"))
        if output_dir:
            output_dir_var.set(output_dir)
            output_dir_label.config(text=os.path.basename(output_dir))

    ttk.Button(settings_frame, text=translate("Seleccionar directorio de salida"), command=select_output_dir).grid(row=1, column=2, sticky="w", padx=5, pady=5)

    # --- Max Tokens ---
    ttk.Label(settings_frame, text=translate("Max Tokens por capítulo:")).grid(row=2, column=0, sticky="w", padx=5, pady=5)
    max_tokens_var = tk.StringVar(value=str(state["config"].get("max_tokens", config_manager.DEFAULT_MAX_TOKENS)))
    max_tokens_entry = ttk.Entry(settings_frame, textvariable=max_tokens_var)
    max_tokens_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

    def validate_max_tokens(new_value):
        if not new_value:
            return True
        try:
            int(new_value)
            return True
        except ValueError:
            return False

    max_tokens_entry.config(validate="key", validatecommand=(settings_frame.register(validate_max_tokens), '%P'))

    # --- Activar/Desactivar Max Tokens ---
    use_max_tokens_var = tk.BooleanVar(value=state["config"].get("use_max_tokens", True))
    use_max_tokens_check = ttk.Checkbutton(settings_frame, text=translate("Usar Max Tokens"), variable=use_max_tokens_var)
    use_max_tokens_check.grid(row=3, column=0, columnspan=3, sticky="w", padx=5, pady=5)

    def save_config_settings():
        """Saves the configuration in the JSON file."""
        if not validate_max_tokens(max_tokens_var.get()):
            messagebox.showerror("Error", translate("Por favor, introduce un número válido para los Max Tokens."))
            return

        state["config"]['api_key'] = api_key_var.get()
        state["config"]['output_dir'] = output_dir_var.get()
        try:
            state["config"]['max_tokens'] = int(max_tokens_var.get())
        except ValueError:
            messagebox.showerror("Error", translate("Por favor, introduce un número válido para los Max Tokens."))
            return
        
        state["config"]['use_max_tokens'] = use_max_tokens_var.get()  # Guardar el estado del checkbutton

        config_manager.save_config(state["config"])

        # Update comboboxes after saving the settings
        state["prompts"] = config_manager.load_prompts(state["config"], state["language"])
        prompt_combobox['values'] = list(state["prompts"].keys())

        state["llm_list"] = config_manager.load_llm_list(state["config"])
        llm_combobox['values'] = state["llm_list"]

        state["settings_window"].destroy()

    ttk.Button(settings_frame, text=translate("Guardar"), command=save_config_settings).grid(row=4, column=0, columnspan=3, pady=20)
    update_gui_text()

def change_language():
    """Cambia el idioma de la interfaz y recarga las traducciones."""
    state["language"] = state["language_combobox"].get()
    state["config"]["language"] = state["language"]
    config_manager.save_config(state["config"])
    load_translations(state["language"])
    update_gui_text()
    
    state["prompts"] = config_manager.load_prompts(state["config"], state["language"])
    prompt_combobox['values'] = list(state["prompts"].keys())

    if 'last_prompt' in state["config"] and state["config"]['last_prompt'] in state["prompts"]:
        prompt_combobox.set(state["config"]['last_prompt'])
        select_prompt()
    else:
        prompt_combobox.set("")
        prompt_label.config(text=f"{translate('Prompt')}: {translate('Ninguno seleccionado')}")
        state["prompt_path"] = ""

    logging.info(f"Idioma cambiado a: {state['language']}") # Agrega este log

def update_gui_text():
    global root, prompt_combobox, prompt_label, llm_combobox, llm_label, pdf_label, chapter_frame, progress_bar, config_button, output_formats_var, progress_label, output_formats_frame, pdf_frame, format_frame, process_button, select_pdf_button, prompt_frame, llm_frame, prompt_label_title, llm_label_title
    root.title(translate("PAPIRE"))
    pdf_label.config(text=f"{translate('PDF')}: {os.path.basename(state['pdf_path'])}" if state["pdf_path"] else f"{translate('PDF')}: {translate('Ninguno seleccionado')}")
    prompt_label.config(text=f"{translate('Prompt')}: {os.path.basename(state['prompt_path'])[:-4]}" if state["prompt_path"] else f"{translate('Prompt')}: {translate('Ninguno seleccionado')}")
    llm_label.config(text=f"LLM: {state['llm_model']}" if state["llm_model"] else f"LLM: {translate('Ninguno seleccionado')}")
    chapter_frame.config(text=translate("Capítulos"))
    config_button.config(text=translate("Configuración"))
    process_button.config(text=translate("Procesar PDF"))
    select_pdf_button.config(text=translate("Seleccionar PDF"))
        
    # Destruir las etiquetas anteriores
    prompt_label_title.destroy()
    llm_label_title.destroy()
    # Crear nuevas etiquetas con el texto traducido
    prompt_label_title = ttk.Label(prompt_frame, text=translate("Seleccionar Prompt"))
    prompt_label_title.grid(row=0, column=0, sticky="w", padx=5, pady=5)
    llm_label_title = ttk.Label(llm_frame, text=translate("Seleccionar Modelo LLM"))
    llm_label_title.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
    for widget in pdf_frame.winfo_children():
        if isinstance(widget, ttk.Button):
             widget.config(text=translate(widget['text']))
    for widget in chapter_frame.winfo_children():
        if isinstance(widget, ttk.Checkbutton) and widget["text"] == "Seleccionar Todos":
             widget.config(text=translate("Seleccionar Todos"))
    
    for widget in format_frame.winfo_children():
        if isinstance(widget,ttk.Label):
            widget.config(text=translate("Formatos de salida:"))
            
    for widget in output_formats_frame.winfo_children():
        if isinstance(widget, ttk.Checkbutton):
            widget.config(text=translate(widget["text"]))
            
    if state["settings_window"] and state["settings_window"].winfo_exists():
         state["settings_window"].title(translate("Configuración"))
         for widget in state["settings_window"].winfo_children()[0].winfo_children():
              if isinstance(widget,ttk.Label):
                 if widget.cget("text") == "API Key de OpenAI:":
                     widget.config(text=translate("API Key de OpenAI:"))
                 elif widget.cget("text") == "Archivo LLMs:":
                    widget.config(text=translate("Archivo LLMs:"))
                 elif widget.cget("text") == "Directorio de Prompts:":
                    widget.config(text=translate("Directorio de Prompts:"))
                 elif widget.cget("text") == "Directorio de Salida:":
                    widget.config(text=translate("Directorio de Salida:"))
                 elif widget.cget("text") == "Max Tokens por capítulo:":
                     widget.config(text=translate("Max Tokens por capítulo:"))
              elif isinstance(widget, ttk.Button):
                    widget.config(text=translate(widget['text']))
    
    progress_label.config(text=translate(progress_label.cget("text")))

def create_gui():
    """Crea la interfaz gráfica principal."""
    global root, prompt_combobox, prompt_label, llm_combobox, llm_label, pdf_label, chapter_frame, progress_bar, config_button, output_formats_var, progress_label, output_formats_frame, pdf_frame, format_frame, process_button, select_pdf_button, select_llm_button, prompt_frame, llm_frame
    
    # --- GUI ---
    root = tk.Tk()
    root.title("PAPIRE")
    root.geometry("900x750")
    root.minsize(900, 800)
    root.resizable(True, True)

    #Estilo
    style = ttk.Style()
    style.theme_use('clam')
    root.columnconfigure(1, weight=1)
    root.rowconfigure(0, weight=0)
    
    # --- Set window icon ---
    icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icons", "logo.ico")
    if os.name == 'nt':  # Windows
        root.iconbitmap(icon_path)
    else:  # macOS y Linux
        icon_image = Image.open(icon_path)
        icon_image = icon_image.resize((256, 256), Image.LANCZOS)
        icon_image_tk = ImageTk.PhotoImage(icon_image)
        root.iconphoto(False, icon_image_tk)

    #Carga de la config
    state["config"] = config_manager.load_config()
    state["language"] = state["config"].get("language", "español")
    load_translations(state["language"])
    state["prompts"] = config_manager.load_prompts(state["config"], state["language"])
    state["llm_list"] = config_manager.load_llm_list(state["config"])
    
    # --- Logo ---
    logo_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icons")
    logo_image = Image.open(os.path.join(logo_dir, "logo.png"))
    
    # Obtener las dimensiones originales
    original_width, original_height = logo_image.size
    
    # Ancho deseado para el logo (puedes cambiar este valor)
    desired_width = 150
    
    # Calcular la nueva altura manteniendo la relación de aspecto
    aspect_ratio = original_height / original_width
    desired_height = int(desired_width * aspect_ratio)
    
    # Redimensionar la imagen con las nuevas dimensiones
    logo_image = logo_image.resize((desired_width, desired_height), Image.LANCZOS)
    logo_icon = ImageTk.PhotoImage(logo_image)

    logo_label = ttk.Label(root, image=logo_icon, style="Transparent.TLabel")
    logo_label.image = logo_icon
    logo_label.grid(row=0, column=0, sticky="nw", padx=10, pady=10)
    style.configure("Transparent.TLabel", background=root.cget("background"), borderwidth=0)

    # --- Config button ---
    icons_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icons")
    gear_image = Image.open(os.path.join(icons_dir, "gear.png"))
    gear_image = gear_image.resize((25, 25), Image.LANCZOS)
    gear_icon = ImageTk.PhotoImage(gear_image)

    config_button = ttk.Button(root, image=gear_icon, command=open_settings, style="Transparent.TButton", text=translate("Configuración"))
    config_button.image = gear_icon
    config_button.grid(row=0, column=3, sticky="ne", padx=10, pady=10)
    style.configure("Transparent.TButton", background=root.cget("background"), borderwidth=0)

    # --- Language Combobox ---
    language_frame = ttk.Frame(root, padding=10)
    language_frame.grid(row=0, column=1, sticky="ne", padx=10, pady=10)
    
    ttk.Label(language_frame, text=translate("Idioma:")).grid(row=0, column=0, sticky="w", padx=5, pady=5)
    
    lang_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "lang")
    language_options = [f.replace(".json", "") for f in os.listdir(lang_dir) if f.endswith(".json")]
    state["language_combobox"] = ttk.Combobox(language_frame, values=language_options)
    state["language_combobox"].set(state["language"])
    state["language_combobox"].grid(row=0, column=1, sticky="ew", padx=5, pady=5)
    state["language_combobox"].bind("<<ComboboxSelected>>", lambda event: change_language())
    
    
    #Configuración de las columnas para que se expandan
    root.columnconfigure(0, weight=0)
    root.columnconfigure(1, weight=1)
    root.columnconfigure(2, weight=0)
    root.columnconfigure(3, weight=0)

    # --- Seleccionar PDF ---
    pdf_frame = ttk.Frame(root, padding=10)
    pdf_frame.grid(row=1, column=0, columnspan=4, sticky="ew", padx=10, pady=10)
    global select_pdf_button
    select_pdf_button, pdf_label = create_button_with_label(pdf_frame, "Seleccionar PDF", select_pdf, 0, 0, "PDF: Ninguno seleccionado")
    pdf_frame.columnconfigure(1, weight=1)
    
    # --- Seleccionar Prompt ---
    prompt_frame = ttk.Frame(root, padding=10)
    prompt_frame.grid(row=2, column=0, columnspan=4, sticky="ew", padx=10, pady=10)
    global prompt_label_title
    prompt_label_title = ttk.Label(prompt_frame, text=translate("Seleccionar Prompt"))
    prompt_label_title.grid(row=0, column=0, sticky="w", padx=5, pady=5)
    prompt_combobox = ttk.Combobox(prompt_frame, values=list(state["prompts"].keys()))
    prompt_combobox.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
    prompt_combobox.bind("<<ComboboxSelected>>", lambda event: select_prompt())
    prompt_label = ttk.Label(prompt_frame, text=f"{translate('Prompt')}: {translate('Ninguno seleccionado')}")
    prompt_label.grid(row=0, column=2, sticky="ew", padx=5, pady=5)
    prompt_frame.columnconfigure(1, weight=1)
    if 'last_prompt' in state["config"] and state["config"]['last_prompt'] in state["prompts"]:
        prompt_combobox.set(state["config"]['last_prompt'])
        select_prompt()

    # --- Seleccionar LLM ---
    llm_frame = ttk.Frame(root, padding=10)
    llm_frame.grid(row=3, column=0, columnspan=4, sticky="ew", padx=10, pady=10)
    global llm_label_title
    llm_label_title = ttk.Label(llm_frame, text=translate("Seleccionar Modelo LLM"))
    llm_label_title.grid(row=0, column=0, sticky="w", padx=5, pady=5)
    llm_combobox = ttk.Combobox(llm_frame, values=state["llm_list"])
    llm_combobox.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
    llm_combobox.bind("<<ComboboxSelected>>", lambda event: select_llm())
    llm_label = ttk.Label(llm_frame, text=f"LLM: {translate('Ninguno seleccionado')}")
    llm_label.grid(row=0, column=2, sticky="ew", padx=5, pady=5)
    llm_combobox.set(state["config"].get("llm_model",config_manager.DEFAULT_LLM_MODEL))
    select_llm()
    llm_frame.columnconfigure(1, weight=1)
    
    # --- Seleccionar Formato ---
    format_frame = ttk.Frame(root, padding=10)
    format_frame.grid(row=4, column=0, columnspan=4, sticky="ew", padx=10, pady=10)
    ttk.Label(format_frame, text=translate("Formatos de salida:")).grid(row=0, column=0, sticky="w", padx=5, pady=5)
    output_formats_frame = ttk.Frame(format_frame)
    output_formats_frame.grid(row=0, column=1, columnspan=2, sticky="ew", padx=5, pady=5)
    output_formats_var = {}
    for i, format_name in enumerate(format_ext.keys()):
      if format_name != "PDF":  # Omitir "PDF"
        var = tk.BooleanVar(value = format_name in state["config"].get("output_formats",["Markdown"]))
        output_formats_var[format_name] = var
        check = ttk.Checkbutton(output_formats_frame, text=translate(format_name), variable=var, command=lambda: update_output_formats())
        check.grid(row=0, column=i, sticky="w", padx=5)

    def update_output_formats():
        state["config"]['output_formats'] = [format_name for format_name, var in output_formats_var.items() if var.get()]
        config_manager.save_config(state["config"])

    # --- Chapter Frame ---
    chapter_frame = ttk.LabelFrame(root, text=translate("Capítulos"), padding=10)
    chapter_frame.grid(row=5, column=0, columnspan=4, sticky="ew", padx=10, pady=10)
    chapter_frame.grid_remove()

    # --- Progress Bar ---
    progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate", style="green.Horizontal.TProgressbar")
    progress_bar.grid(row=6, column=0, columnspan=4, sticky="ew", padx=10, pady=10)
    progress_bar.grid_remove()
    progress_label = ttk.Label(root, text="")
    progress_label.grid(row=6, column=0, columnspan=4, sticky="ew", padx=10)
    
    # Estilo de la barra de progreso
    style.configure("green.Horizontal.TProgressbar", foreground='green', background='green')

    # --- Botón de Procesar ---
    process_button = ttk.Button(root, text=translate("Procesar PDF"), command=process_pdf)
    process_button.grid(row=7, column=0, columnspan=4, pady=20)

    # Configuración de las columnas para que se expandan
    root.columnconfigure(0, weight=0)
    root.columnconfigure(1, weight=1)
    root.columnconfigure(2, weight=0)
    root.columnconfigure(3, weight=0)
    
    update_gui_text() # Llama a update_gui_text() aquí, después de que todos los widgets estén definidos.
    
    root.mainloop()