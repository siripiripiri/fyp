import os
import json
import base64
import mimetypes
import gradio as gr
import pdfplumber
from PIL import Image
from datetime import datetime
from openai import OpenAI

client = OpenAI(
    api_key="OPENAI_API_KEY"
)

def get_questions_from_text(text, question_type):
    prompt = f"""
You are a machine that returns only JSON-like output as plain text, without any markdown.

Generate as many {question_type} type questions and answers based on the following:

{text}

If the image contains diagrams, equations, tables, or graphs, interpret the topic & context and include questions related to those elements as well.

Return in this format:
{{
  "questions": [
    {{
      "question": "What is ...?",
      "answer": "..."
    }}
  ]
}}

Do not return anything except the JSON-like object as plain text, without any markdown.
"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# Convert image to base64 data URL
def image_to_data_url(img_path):
    mime_type, _ = mimetypes.guess_type(img_path)
    with open(img_path, "rb") as f:
        b64_data = base64.b64encode(f.read()).decode()
    return f"data:{mime_type};base64,{b64_data}"

# Function to generate QA from image
def get_questions_from_image(image_path, question_type):
    data_url = image_to_data_url(image_path)
    prompt = f"""
You are a machine that returns only JSON-like output as plain text, without markdown.

Based on the image, generate as many {question_type} type questions and answers as possible.

Return in this format:
{{
  "questions": [
    {{
      "question": "",
      "answer": ""
    }}
  ]
}}

If the image contains diagrams, equations, tables, or graphs, interpret the topic & context and include questions related to those elements as well.


Do not return anything except the JSON-like object as plain text, without any markdown.
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
    )
    return response.choices[0].message.content

def save_response(raw_text):
    os.makedirs("responses", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join("responses", f"qa_{timestamp}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(raw_text)

def process_file(file, question_type):
    if not file:
        return "No file uploaded."

    ext = os.path.splitext(file.name)[1].lower()

    if ext == ".pdf":
        with pdfplumber.open(file) as pdf:
            text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        if not text.strip():
            return "No extractable text found in PDF."
        raw_output = get_questions_from_text(text, question_type)

    elif ext in [".png", ".jpg", ".jpeg", ".heic", ".webp"]:
        raw_output = get_questions_from_image(file.name, question_type)

    else:
        return f"Unsupported file type: {ext}"

    save_response(raw_output)
    return raw_output

# Gradio UI setup
with gr.Blocks() as app:
    gr.Markdown("# ZAPDOS — PDF & Image Question Generator")

    with gr.Row():
        with gr.Column():
            question_type = gr.Radio(
                ["MCQs", "Short Answer", "Fill-in-the-Blanks", "One-word Answer"],
                label="Select Question Type"
            )
            uploaded_file = gr.File(
                label="Upload PDF or Image",
                file_types=[".pdf", ".png", ".jpg", ".jpeg", ".heic", ".webp"]
            )
            generate_btn = gr.Button("Generate Questions")

        with gr.Column():
            output_display = gr.Textbox(
                label="Generated Questions (Plain Text)",
                interactive=False,
                lines=25,
                type="text"
            )

    generate_btn.click(fn=process_file, inputs=[uploaded_file, question_type], outputs=output_display)

# Launch the app
if __name__ == "__main__":
    app.launch()
