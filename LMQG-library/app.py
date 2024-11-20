import gradio as gr
import tiktoken
from lmqg import TransformersQG
import pdfplumber

# Function to read PDF file using pdfplumber
def read_pdf_with_pdfplumber(file):
    text = ''
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text()
    return text

# Function to tokenize text and split into chunks of 500 tokens
def chunk_text(text, chunk_size=500):
    enc = tiktoken.get_encoding("cl100k_base")  # GPT-3.5/4 encoding
    tokens = enc.encode(text)  # Tokenize the text
    chunks = [tokens[i:i + chunk_size] for i in range(0, len(tokens), chunk_size)]
    return chunks

# Function to process PDF and generate QA pairs
def process_pdf(file):
    # Read PDF content
    pdf_text = read_pdf_with_pdfplumber(file.name)
    
    # Chunk the text into smaller pieces
    text_chunks = chunk_text(pdf_text, chunk_size=400)
    
    # Decode the first chunk for demo purposes
    decoded_chunk = tiktoken.get_encoding("cl100k_base").decode(text_chunks[0])

    # Load the Transformers model and generate QA from the first chunk
    model = TransformersQG(language="en")
    qa = model.generate_qa(decoded_chunk)
    
    return qa

# Create Gradio Interface
def gradio_app():
    # File uploader for PDF and output for QA pairs
    with gr.Blocks() as demo:
        gr.Markdown("### PDF to Question-Answer Generator")
        
        with gr.Row():
            pdf_input = gr.File(label="Upload PDF", file_types=['.pdf'])
            output = gr.JSON(label="Generated Q&A")
        
        # Button to trigger processing
        generate_btn = gr.Button("Generate Q&A")
        
        # Define action when button is clicked
        generate_btn.click(fn=process_pdf, inputs=pdf_input, outputs=output)
    
    return demo

# Run the Gradio app
app = gradio_app()
app.launch()
