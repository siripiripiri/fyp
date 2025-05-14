import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.summarizers.luhn import LuhnSummarizer
import gradio as gr
import pdfplumber

# Download required NLTK data
nltk.download('punkt')
nltk.download('punkt_tab')

class TextProcessor:
    def __init__(self):
        self.summarizers = {
            'text_rank': TextRankSummarizer(),
            'lex_rank': LexRankSummarizer(),
            'lsa': LsaSummarizer(),
            'luhn': LuhnSummarizer()
        }
        self.smooth = SmoothingFunction().method1

    def chunk_text(self, text, max_words=500):
        """Split text into chunks of maximum word count."""
        sentences = sent_tokenize(text)
        chunks = []
        current_chunk = []
        current_word_count = 0

        for sentence in sentences:
            words = word_tokenize(sentence)
            if current_word_count + len(words) > max_words and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_word_count = len(words)
            else:
                current_chunk.append(sentence)
                current_word_count += len(words)

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def get_summary(self, text, method, sentences_count=3):
        """Generate summary using specified method."""
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = self.summarizers[method]
        summary = summarizer(parser.document, sentences_count)
        return ' '.join([str(sentence) for sentence in summary])

    def evaluate_summaries(self, original_text, summaries):
        """Evaluate summaries using BLEU score."""
        # Tokenize original text into sentences
        original_sentences = sent_tokenize(original_text)
        reference = [word_tokenize(sent) for sent in original_sentences]
        
        # Calculate BLEU scores for each summary
        similarities = {}
        for method, summary in summaries.items():
            # Tokenize summary
            hypothesis = word_tokenize(summary)
            # Calculate BLEU score
            score = sentence_bleu(reference, hypothesis, smoothing_function=self.smooth)
            similarities[method] = score

        # Find best method
        best_method = max(similarities.items(), key=lambda x: x[1])[0]
        return similarities, best_method

    def process_text(self, text):
        """Process text through the complete pipeline."""
        # Split into chunks
        chunks = self.chunk_text(text)
        
        # Evaluate methods on first chunk
        first_chunk = chunks[0]
        summaries = {
            method: self.get_summary(first_chunk, method)
            for method in self.summarizers.keys()
        }
        
        similarities, best_method = self.evaluate_summaries(first_chunk, summaries)
        
        # Process remaining chunks with best method
        processed_chunks = []
        for chunk in chunks[1:]:
            summary = self.get_summary(chunk, best_method)
            processed_chunks.append(summary)
        
        # Combine first chunk summary with processed chunks
        final_text = summaries[best_method] + ' ' + ' '.join(processed_chunks)
        
        return {
            'final_text': final_text,
            'best_method': best_method,
            'method_scores': similarities,
            'chunk_count': len(chunks)
        }

    def test_pipeline(self, file):
        """Test the pipeline and display intermediate results."""
        if not file:
            return "No file uploaded."

        # Extract text from PDF
        with pdfplumber.open(file) as pdf:
            text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        
        if not text.strip():
            return "No extractable text found in PDF."

        # Get chunks
        chunks = self.chunk_text(text)
        
        # Print first two chunks
        print("\n=== First Two Chunks ===")
        for i, chunk in enumerate(chunks[:2], 1):
            print(f"\nChunk {i}:")
            print(chunk[:500] + "..." if len(chunk) > 500 else chunk)
        
        # Get summaries for first chunk
        first_chunk = chunks[0]
        summaries = {
            method: self.get_summary(first_chunk, method)
            for method in self.summarizers.keys()
        }
        
        # Evaluate methods
        similarities, best_method = self.evaluate_summaries(first_chunk, summaries)
        
        # Print method scores
        print("\n=== Method Scores (BLEU) ===")
        for method, score in similarities.items():
            print(f"{method}: {score:.4f}")
        
        print(f"\nBest Method: {best_method}")
        
        # Print first three summaries using best method
        print("\n=== First Three Summaries (Best Method) ===")
        for i, chunk in enumerate(chunks[:3], 1):
            summary = self.get_summary(chunk, best_method)
            print(f"\nSummary {i}:")
            print(summary)
        
        return "Check terminal for detailed output"

def create_test_interface():
    """Create a Gradio interface for testing the text processor."""
    processor = TextProcessor()
    
    with gr.Blocks() as test_app:
        gr.Markdown("# Text Processor Testing Interface")
        
        with gr.Row():
            with gr.Column():
                test_file = gr.File(
                    label="Upload PDF for Testing",
                    file_types=[".pdf"]
                )
                test_btn = gr.Button("Test Pipeline")
            
            with gr.Column():
                output = gr.Textbox(
                    label="Status",
                    interactive=False,
                    lines=5
                )
        
        test_btn.click(
            fn=processor.test_pipeline,
            inputs=[test_file],
            outputs=[output]
        )
    
    return test_app

if __name__ == "__main__":
    test_app = create_test_interface()
    test_app.launch() 