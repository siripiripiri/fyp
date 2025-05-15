import re
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.tag import pos_tag
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
import spacy
import pdfplumber
import json

# Download required NLTK data
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('stopwords')
nltk.download('punkt_tab')
nltk.download('averaged_perceptron_tagger_eng')

def preprocess_text(text):
    """Clean and normalize extracted PDF text"""
    # Remove extra whitespace and normalize line breaks
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters while preserving sentence structure
    text = re.sub(r'[^\w\s.,!?]', '', text)
    return text.strip()

def extract_key_sentences(text, top_n=10):
    """Identify most important sentences based on key phrases and structural indicators"""
    # Split into sentences
    sentences = sent_tokenize(text)
    
    # Important phrase patterns
    importance_markers = [
        r'importantly',
        r'significantly',
        r'key (point|concept|idea)',
        r'main (point|concept|idea)',
        r'in conclusion',
        r'therefore',
        r'as a result',
        r'this means',
        r'for example'
    ]
    
    # Score sentences based on multiple criteria
    sentence_scores = []
    for sentence in sentences:
        score = 0
        
        # Check for importance markers
        for marker in importance_markers:
            if re.search(marker, sentence.lower()):
                score += 2
                
        # Check for subject-verb-object structure
        tokens = pos_tag(word_tokenize(sentence))
        has_noun = any(tag.startswith('NN') for word, tag in tokens)
        has_verb = any(tag.startswith('VB') for word, tag in tokens)
        if has_noun and has_verb:
            score += 1
            
        # Favor medium-length sentences (not too short or long)
        words = len(word_tokenize(sentence))
        if 10 <= words <= 30:
            score += 1
            
        sentence_scores.append((sentence, score))
    
    # Return top scoring sentences
    return [sent for sent, score in sorted(sentence_scores, key=lambda x: x[1], reverse=True)[:top_n]]

def identify_key_concepts(text):
    """Extract key concepts using NLP techniques"""
    nlp = spacy.load('en_core_web_sm')
    doc = nlp(text)
    
    concepts = []
    
    # Extract named entities
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    
    # Extract noun phrases
    noun_phrases = [chunk.text for chunk in doc.noun_chunks]
    
    # Use TF-IDF to identify important terms
    vectorizer = TfidfVectorizer(max_features=20, stop_words='english')
    tfidf_matrix = vectorizer.fit_transform([text])
    important_terms = dict(zip(vectorizer.get_feature_names_out(), tfidf_matrix.toarray()[0]))
    
    # Combine and deduplicate findings
    concepts.extend([ent[0] for ent in entities])
    concepts.extend(noun_phrases)
    concepts.extend(important_terms.keys())
    
    return list(set(concepts))

def generate_questions(key_sentences, key_concepts):
    """Generate different types of questions based on key content"""
    questions = []
    
    # Question templates
    templates = {
        'definition': "What is {concept}?",
        'explanation': "Can you explain how {concept} works?",
        'relationship': "What is the relationship between {concept1} and {concept2}?",
        'application': "How is {concept} applied in practice?",
        'implication': "What are the implications of {sentence}?",
        'comparison': "How does {concept1} differ from {concept2}?",
    }
    
    # Generate concept-based questions
    for concept in key_concepts[:5]:  # Limit to top 5 concepts
        questions.append(templates['definition'].format(concept=concept))
        questions.append(templates['application'].format(concept=concept))
        
        # Generate relationship questions between concepts
        for concept2 in key_concepts[:5]:
            if concept != concept2:
                questions.append(templates['relationship'].format(
                    concept1=concept, 
                    concept2=concept2
                ))
    
    # Generate questions based on key sentences
    for sentence in key_sentences[:3]:  # Limit to top 3 sentences
        questions.append(templates['implication'].format(sentence=sentence))
    
    return list(set(questions))  # Remove duplicates

def process_pdf_text(text):
    """Main function to process PDF text and generate questions"""
    # Clean the text=
    cleaned_text = preprocess_text(text)
    
    # Extract key sentences and concepts
    key_sentences = extract_key_sentences(cleaned_text)
    key_concepts = identify_key_concepts(cleaned_text)
    
    # Generate questions
    questions = generate_questions(key_sentences, key_concepts)
    
    return {
        'key_sentences': key_sentences,
        'key_concepts': key_concepts,
        'generated_questions': questions
    }

if __name__ == "__main__":
    pdf_path = "Study-Documents/UNIT -6.pdf"
    output_path = "Results/questions.json"
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""  # Handle cases where text might be None
    text.strip()
    

    results=process_pdf_text(text)
    with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)

    
    # print(results)
