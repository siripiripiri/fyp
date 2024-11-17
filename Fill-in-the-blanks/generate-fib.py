import PyPDF2
from transformers import pipeline
import nltk
from nltk.tokenize import sent_tokenize
from nltk.tag import pos_tag
from nltk.chunk import ne_chunk
import json
import random
import pdfplumber

class QuestionGenerator:
    def __init__(self):
        # Initialize NLTK and download required data
        nltk.download('punkt')
        nltk.download('averaged_perceptron_tagger')
        nltk.download('maxent_ne_chunker')
        nltk.download('words')
        nltk.download('averaged_perceptron_tagger_eng')
        nltk.download('maxent_ne_chunker_tab')
        
        # Initialize the NLP pipelines
        self.qa_pipeline = pipeline('question-answering')
        self.text_generator = pipeline('text-generation', model='gpt2')
        
    def get_input_text(self, pdf_path):
        """Extract text from PDF file"""
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""  # Handle cases where text might be None
        return text.strip()
    
    def sent_tokenize(self, text):
        """Split text into sentences"""
        return sent_tokenize(text)
    
    def find_potential_answers(self, sentence):
        """Find potential answers in a sentence using POS tagging and NER"""
        # Tag parts of speech
        tokens = nltk.word_tokenize(sentence)
        pos_tags = pos_tag(tokens)
        
        # Find named entities
        named_entities = ne_chunk(pos_tags)
        
        potential_answers = []
        
        # Extract noun phrases and named entities
        current_chunk = []
        for i, (word, tag) in enumerate(pos_tags):
            if tag.startswith(('NN', 'JJ')):  # Nouns and adjectives
                current_chunk.append(word)
            elif current_chunk:
                if len(' '.join(current_chunk)) > 2:  # Minimum length check
                    potential_answers.append(' '.join(current_chunk))
                current_chunk = []
        
        # Add any remaining chunk
        if current_chunk:
            potential_answers.append(' '.join(current_chunk))
            
        # Remove duplicates while preserving order
        potential_answers = list(dict.fromkeys(potential_answers))
        
        return potential_answers[:3]  # Limit to top 3 answers per sentence
    
    def validate_answer(self, sentence, answer):
        """Validate if the answer makes sense using question-answering model"""
        try:
            # Generate a simple question about the answer
            question = f"What is {answer}?"
            
            result = self.qa_pipeline(
                question=question,
                context=sentence
            )
            
            # Check if the model's confidence score is high enough
            return result['score'] > 0.1
        except Exception:
            return False
    
    def create_fill_in_blank(self, sentence, answer):
        """Create a fill-in-the-blank question from a sentence and answer"""
        # Replace the answer with a blank of appropriate length
        blank_length = len(answer)
        blank = '_' * blank_length
        
        # Make sure we're replacing the exact answer
        question = sentence.replace(answer, blank)
        
        return question
    
    def generate_questions(self, pdf_path):
        """Main function to generate fill-in-the-blank questions from PDF"""
        # Get input text from PDF
        context = self.get_input_text(pdf_path)
        
        # Split into sentences
        sentences = self.sent_tokenize(context)
        
        output_dict = {
            'questions': []
        }
        
        # Process each sentence
        for sentence in sentences:
            # Skip very short sentences
            if len(sentence.split()) < 5:
                continue
            
            # Find potential answers in the sentence
            potential_answers = self.find_potential_answers(sentence)
            
            # Create fill-in-the-blank questions for valid answers
            for answer in potential_answers:
                # Skip if answer is too short
                if len(answer) < 3:
                    continue
                
                # Validate the answer
                if not self.validate_answer(sentence, answer):
                    continue
                
                # Create the fill-in-blank question
                fib_question = self.create_fill_in_blank(sentence, answer)
                
                # Add to output dictionary
                output_dict['questions'].append({
                    'question': fib_question,
                    'answer': answer,
                    'original_sentence': sentence
                })
                break # so there is just one variation of a question
        
        return output_dict
    
    def save_questions(self, questions, output_path):
        """Save generated questions to a JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(questions, f, indent=2)

# Example usage
if __name__ == "__main__":
    generator = QuestionGenerator()
    
    # Generate questions from a PDF file
    pdf_path = "Study-Documents/UNIT -6.pdf"
    output_path = "Fill-in-the-blanks/questions-fib.json"
    
    questions = generator.generate_questions(pdf_path)
    generator.save_questions(questions, output_path)
    
    # Print example questions
    print("\nGenerated Questions:")
    for i, qa in enumerate(questions['questions'][:5], 1):
        print(f"\nQuestion {i}:")
        print(f"Fill in the blank: {qa['question']}")
        print(f"Answer: {qa['answer']}")