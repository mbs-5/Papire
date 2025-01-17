import openai
from tkinter import messagebox
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def summarize_with_openai(model, prompt, text, max_tokens=None):
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": text}
    ]
    if max_tokens:
      response = openai.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        )
    else:
      response = openai.chat.completions.create(
        model=model,
        messages=messages,
        )
    return response.choices[0].message.content.strip()

def split_text(text, max_length):
    """Divide un texto en partes más pequeñas."""
    if len(text) <= max_length:
        return [text]

    parts = []
    start = 0
    while start < len(text):
        end = start + max_length
        if end >= len(text):
            parts.append(text[start:])
            break

        while end > start and text[end] not in [' ', '\n']:
            end -= 1

        if end <= start:
            end = start + max_length

        parts.append(text[start:end])
        start = end
    logging.info(f"Texto dividido en partes de {max_length} caracteres.")
    return parts