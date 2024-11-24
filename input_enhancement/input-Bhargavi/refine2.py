import spacy
from collections import defaultdict
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import networkx as nx
from sentence_transformers import SentenceTransformer
import json
import pdfplumber
import re

class SemanticQuestionGenerator:
    def __init__(self):
        # Load models
        self.nlp = spacy.load('en_core_web_sm')
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def extract_semantic_relationships(self, text):
        """Extract semantic relationships between concepts"""
        doc = self.nlp(text)
        relationships = []
        
        # Create a graph to store concept relationships
        concept_graph = nx.Graph()
        
        # Extract subject-verb-object relationships
        for sent in doc.sents:
            sent_doc = self.nlp(sent.text)
            
            # Find main subject and object
            subject = None
            obj = None
            verb = None
            
            for token in sent_doc:
                if "subj" in token.dep_:
                    # Get the full noun phrase
                    subject = ' '.join([t.text for t in token.subtree])
                elif "obj" in token.dep_:
                    # Get the full noun phrase
                    obj = ' '.join([t.text for t in token.subtree])
                elif token.pos_ == "VERB":
                    verb = token.text
                    
            if subject and obj and verb:
                relationships.append({
                    'subject': subject,
                    'verb': verb,
                    'object': obj,
                    'sentence': sent.text
                })
                
                # Add to concept graph
                concept_graph.add_edge(subject, obj, relationship=verb)
                
        return relationships, concept_graph

    def identify_concept_hierarchy(self, text):
        """Identify hierarchical relationships between concepts"""
        doc = self.nlp(text)
        hierarchy = defaultdict(list)
        
        # Look for hierarchical patterns
        patterns = [
            "is a type of",
            "is part of",
            "consists of",
            "contains",
            "belongs to"
        ]
        
        for sent in doc.sents:
            for pattern in patterns:
                if pattern in sent.text.lower():
                    parts = sent.text.lower().split(pattern)
                    if len(parts) == 2:
                        child = parts[0].strip()
                        parent = parts[1].strip()
                        hierarchy[parent].append(child)
                        
        return hierarchy

    def calculate_concept_similarity(self, concepts):
        """Calculate semantic similarity between concepts"""
        if not concepts:  # Check if concepts list is empty
            return []
            
        # Encode concepts using sentence transformer
        concept_embeddings = self.sentence_model.encode(concepts)
        
        # Calculate similarity matrix
        similarity_matrix = cosine_similarity(concept_embeddings)
        
        # Create similarity pairs
        similarity_pairs = []
        for i in range(len(concepts)):
            for j in range(i + 1, len(concepts)):
                similarity_pairs.append({
                    'concept1': concepts[i],
                    'concept2': concepts[j],
                    'similarity': similarity_matrix[i][j]
                })
                
        return sorted(similarity_pairs, key=lambda x: x['similarity'], reverse=True)

    def generate_semantic_questions(self, text):
        """Generate questions based on semantic understanding"""
        # Extract relationships and build concept graph
        relationships, concept_graph = self.extract_semantic_relationships(text)
        
        # Identify concept hierarchy
        hierarchy = self.identify_concept_hierarchy(text)
        
        # Get all unique concepts
        concepts = list(set([rel['subject'] for rel in relationships] + 
                          [rel['object'] for rel in relationships]))
        
        # Calculate concept similarities
        similarities = self.calculate_concept_similarity(concepts)
        
        questions = []
        
        # Generate relationship-based questions
        for rel in relationships:
            # Causal relationships
            if any(verb in rel['verb'].lower() for verb in ['cause', 'lead', 'result']):
                questions.append(f"How does {rel['subject']} cause or influence {rel['object']}?")
                questions.append(f"What are the mechanisms through which {rel['subject']} affects {rel['object']}?")
            
            # Process relationships
            if any(verb in rel['verb'].lower() for verb in ['process', 'transform', 'change']):
                questions.append(f"Can you explain the process by which {rel['subject']} {rel['verb']} {rel['object']}?")
                questions.append(f"What are the key stages in the {rel['verb']} process between {rel['subject']} and {rel['object']}?")
            
            # Descriptive relationships
            questions.append(f"What is the relationship between {rel['subject']} and {rel['object']}?")
            questions.append(f"How does {rel['subject']} interact with {rel['object']}?")
        
        # Generate hierarchy-based questions
        for parent, children in hierarchy.items():
            if len(children) > 1:
                questions.append(f"How do {', '.join(children[:-1])} and {children[-1]} differ as types of {parent}?")
                questions.append(f"What characteristics define {parent} and how are they manifested in its subtypes?")
        
        # Generate similarity-based questions
        for sim in similarities[:5]:  # Top 5 similar concepts
            if sim['similarity'] > 0.7:  # Only for highly similar concepts
                questions.append(f"What key factors differentiate {sim['concept1']} from {sim['concept2']} despite their similarities?")
                questions.append(f"How do the applications of {sim['concept1']} and {sim['concept2']} differ in practice?")
        
        # Generate analytical questions based on graph centrality
        if concept_graph.nodes():  # Check if graph has nodes
            central_concepts = sorted(nx.degree_centrality(concept_graph).items(), 
                                    key=lambda x: x[1], reverse=True)
            for concept, centrality in central_concepts[:3]:
                questions.append(f"How does {concept} interact with and influence other key concepts in this domain?")
                questions.append(f"What makes {concept} a central concept and how does it connect to related ideas?")
        
        return list(set(questions))  # Remove any duplicates
    
def preprocess_text(text):
    """Clean and normalize extracted PDF text"""
    # Remove extra whitespace and normalize line breaks
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters while preserving sentence structure
    text = re.sub(r'[^\w\s.,!?]', '', text)
    return text.strip()

def process_text_for_questions(text):
    """Main function to process text and generate semantic questions"""
    generator = SemanticQuestionGenerator()
    
    text=preprocess_text(text)
    # Generate questions
    questions = generator.generate_semantic_questions(text)
    
    # Extract relationships for context
    relationships, concept_graph = generator.extract_semantic_relationships(text)
    
    # Get concept hierarchy
    hierarchy = generator.identify_concept_hierarchy(text)
    
    return {
        'questions': questions,
        'relationships': relationships,
        'hierarchy': hierarchy,
        'concept_graph': concept_graph
    }


if __name__ == "__main__":
    pdf_path = "Study-Documents/UNIT -6.pdf"
    output_path = "Results/questions2.json"
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""  # Handle cases where text might be None
    text.strip()
    

    results=process_text_for_questions(text)
    questions=results['questions']
    with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(questions, f, indent=2)

    
    # print(results)