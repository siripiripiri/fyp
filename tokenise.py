import PyPDF2
import tiktoken
from lmqg import TransformersQG
import pdfplumber

# Function to read PDF file
def read_pdf_with_pdfplumber(file_path):
    text = ''
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text()
    return text

def read_pdf(file_path):
    pdf_reader = PyPDF2.PdfReader(file_path)
    text = ''
    for page in range(len(pdf_reader.pages)):
        text += pdf_reader.pages[page].extract_text()
    return text

# Function to tokenize text and split into chunks of 500 tokens
def chunk_text(text, chunk_size=500):
    enc = tiktoken.get_encoding("cl100k_base")  # GPT-3.5/4 encoding
    tokens = enc.encode(text)  # Tokenize the text
    chunks = [tokens[i:i + chunk_size] for i in range(0, len(tokens), chunk_size)]
    return chunks

# Path to your PDF file
file_path = 'UNIT -6.pdf'

# Read and process the PDF
pdf_text = read_pdf_with_pdfplumber(file_path)
text_chunks = chunk_text(pdf_text, chunk_size=400)

# Decode and print the chunks
# for idx, chunk in enumerate(text_chunks):
#     decoded_chunk = tiktoken.get_encoding("cl100k_base").decode(chunk)
#     print(f"Chunk {idx + 1}:\n{decoded_chunk}\n")

decoded_chunk = tiktoken.get_encoding("cl100k_base").decode(text_chunks[0])
print(decoded_chunk)

model = TransformersQG(language="en")
context = decoded_chunk

qa = model.generate_qa(context)
print(qa)