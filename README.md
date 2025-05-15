# Flashcard Generation Web App

An intelligent flashcard generator that uses AI to create personalized flashcards from your documents, with spaced repetition learning.

## Features

- 📁 Upload multiple file types (PDF, DOCX, PPT, images, text)
- 🔄 Extract and process text from documents
- 🧠 Generate question-answer pairs using AI
- 🃏 Interactive flashcard interface with animations
- ✅ Answer checking with feedback
- 📊 Spaced repetition algorithm (SM-2) for optimized learning
- 📱 Responsive design for all devices

## Tech Stack

### Frontend
- React.js with Vite
- CSS animations and transitions
- Responsive design

### Backend
- Python Flask API
- OCR for image text extraction (pytesseract)
- Document processing (PyPDF2, python-docx, python-pptx)
- OpenAI GPT-4 integration for flashcard generation

## Setup Instructions

### Prerequisites
- Node.js (v14 or higher)
- Python (v3.8 or higher)
- OpenAI API key

### Backend Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install Flask Flask-CORS pytesseract PyPDF2 python-docx python-pptx opencv-python numpy requests openai
```

3. Install Tesseract OCR (for image processing):
   - On Ubuntu: `sudo apt-get install tesseract-ocr`
   - On macOS: `brew install tesseract`
   - On Windows: Download and install from [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)

4. Set your OpenAI API key:
```bash
# Linux/Mac
export OPENAI_API_KEY="your-api-key-here"

# Windows
set OPENAI_API_KEY="your-api-key-here"
```

5. Start the Flask server:
```bash
python app.py
```

### Frontend Setup

1. Navigate to the project directory and install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. Open your browser and go to http://localhost:3000

## Usage

1. Upload a document (PDF, DOCX, PPT, image, or text file)
2. Wait for the AI to process the file and generate flashcards
3. Answer each flashcard question and get immediate feedback
4. Rate the difficulty of each question
5. Review cards based on the spaced repetition algorithm

## License

This project is licensed under the MIT License - see the LICENSE file for details.