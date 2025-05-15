import os
import json
import base64
import mimetypes
import tempfile
from datetime import datetime
import time 
import concurrent.futures 
import re
import openai
from flask import Flask, request, jsonify
from flask_cors import CORS

import pdfplumber
from PIL import Image, UnidentifiedImageError # For image processing
from werkzeug.utils import secure_filename

from openai import OpenAI

# Import sent_tokenize for app.py as well for chunking
from nltk.tokenize import sent_tokenize 
import nltk 

from summarizer import process_text_for_qna 
# is_likely_boilerplate_page is used internally by process_text_for_qna

app = Flask(__name__)
CORS(app)

# Download NLTK punkt tokenizer if not already present (for sent_tokenize in app.py)
try:
    nltk.data.find('tokenizers/punkt')
except nltk.downloader.DownloadError:
    print("[NLTK_APP] 'punkt' tokenizer not found for app.py. Downloading...")
    nltk.download('punkt', quiet=True)


OPENAI_API_KEY = "" # Your actual OpenAI key

OPENAI_INPUT_USE_FULL_TEXT_IF_SHORTER_THAN_CHARS = 35000
MAX_CHARS_PER_CHUNK_FOR_OPENAI = 75000 
MAX_WORKERS_FOR_CHUNKING = 1 

openai_client = None
if not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_ACTUAL_OPENAI_API_KEY_PLACEHOLDER": # More generic placeholder check
    print("FATAL ERROR: OpenAI API Key is not correctly hardcoded or is a placeholder.")
else:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("OpenAI client configured successfully.")
    except Exception as e:
        print(f"FATAL ERROR: Could not configure OpenAI client: {e}")

OPENAI_MODEL_NAME = "gpt-4o"

def get_questions_from_text_openai(text_content, question_type_selected, source_page_numbers=None, num_meaningful_pages_in_source=0, is_chunked=False, chunk_info=""):
    if not openai_client:
        raise ConnectionError("OpenAI client is not configured.")
    
    type_specific_instructions = ""
    mcq_options_field_example = ""
    json_structure_note = """The "options" field must be an array of strings ONLY for "MCQs" type; for other types, it must be null or omitted entirely. The "source_page" field must always be present in each question object, its value can be a string (single page, or comma-separated list) or null if not determinable."""

    if question_type_selected == "MCQs":
        type_specific_instructions = "For MCQs: The main 'question' field poses the inquiry. Include an 'options' field as an array of 3 to 4 distinct string choices. The 'answer' field must contain ONLY the text of the correct option from this 'options' array."
        mcq_options_field_example = '\n      "options": ["Option Alpha", "Option Beta", "Correct Option Gamma", "Option Delta"],'
    elif question_type_selected == "Fill-in-the-Blanks": type_specific_instructions = "For Fill-in-the-Blanks, 'question' uses '_____' for blanks, 'answer' is the filling."
    elif question_type_selected == "True or False": type_specific_instructions = "For True or False, 'question' is a statement, 'answer' is 'True' or 'False'."
    elif question_type_selected == "One-word Answer": type_specific_instructions = "For One-word Answer, 'answer' is a single, highly specific keyword or very short phrase directly from the text."
    elif question_type_selected == "Short Answer": type_specific_instructions = "For Short Answer, 'answer' is a concise explanation, definition, or response, typically 1-3 sentences long."

    page_context_instruction = ""
    if source_page_numbers:
        page_numbers_str_list = [str(p) for p in source_page_numbers if p is not None] 
        page_numbers_str = ", ".join(sorted(list(set(page_numbers_str_list))))
        if page_numbers_str:
             page_context_instruction = f"The provided text content is derived from material spanning page(s) {page_numbers_str} of an original document which has {num_meaningful_pages_in_source} meaningful content pages. For each question generated, you MUST include a 'source_page' field. This field should indicate the specific page number (or comma-separated list of page numbers if a concept spans multiple pages) from the set [{page_numbers_str}] that the question most directly pertains to. If a specific page cannot be determined for a question despite the context, set its 'source_page' field to null."
    else:
        page_context_instruction = "Set the 'source_page' field to null for each question as source page information is not available for this content."
    
    num_desired_questions = 0
    estimated_words = len(text_content.split())
    if len(text_content) > 0:
        base_qs_from_length = max(10, int(estimated_words / 100)) # ~1 question per 100 words as a base, min 10
        
        if is_chunked:
            num_desired_questions = min(base_qs_from_length, 30) # Cap per chunk, e.g., max 30
        else: # Full document (or single large block that wasn't chunked)
            # Use num_meaningful_pages_in_source if available for a better estimate for the whole doc
            if num_meaningful_pages_in_source > 0:
                num_desired_questions = max(15, min(num_meaningful_pages_in_source * 2, 200)) # Up to 2 Qs per original page, max 200
            else: # Fallback if no page count, use text length more aggressively for full doc
                num_desired_questions = min(base_qs_from_length * 2, 200) # Cap at 200
        num_desired_questions = max(10, num_desired_questions) # Absolute minimum
    else: 
        num_desired_questions = 10 # Default if text_content somehow empty

    quantity_instruction = f"CRITICAL INSTRUCTION: Generate an EXTREMELY COMPREHENSIVE and LARGE set of questions from the provided text (length: {len(text_content)} characters, ~{estimated_words} words). Your primary goal is to maximize the number of high-quality, distinct questions. Aim to generate AT LEAST {max(10, num_desired_questions)} questions. If the content is rich and detailed, generate SIGNIFICANTLY MORE, up to {num_desired_questions + 50} or AS MANY questions as the text can meaningfully support, to ensure exhaustive coverage. Do not be conservative with the quantity; extract every possible question-worthy piece of information. Ensure questions cover a wide range of difficulties and topics from THIS text block."
    if is_chunked:
        quantity_instruction = f"This is text chunk {chunk_info}. CRITICAL INSTRUCTION: From THIS CHUNK (length: {len(text_content)} characters, ~{estimated_words} words), generate as many high-quality, distinct questions as possible, ideally around {num_desired_questions}, but feel free to generate more (up to {num_desired_questions + 10}) if the content supports it. Ensure comprehensive coverage of THIS CHUNK."

    prompt = f"""
You are an AI that generates a large volume of high-quality educational flashcard questions from text. Output MUST be a single, valid JSON object. No markdown or other text.

Text to process:
---
{text_content}
---

Instructions:
1. Generate questions of type: "{question_type_selected}".
2. {page_context_instruction}
3. Specific instructions for "{question_type_selected}": {type_specific_instructions}
4. {quantity_instruction}
5. Questions should vary in difficulty from simple recall to requiring moderate comprehension, covering diverse aspects and details of the text. Ensure variety.

Required JSON Output Structure:
{{
  "questions": [
    {{
      "id": "unique_id_1", "question_type": "{question_type_selected}",
      "question": "...",{mcq_options_field_example} "answer": "...",
      "source_page": "page_num_or_list_or_null"
    }}
  ]
}}
{json_structure_note} Each "id" must be unique.
"""
    messages = [
        {"role": "system", "content": "You are an AI assistant specialized in generating a large number of diverse, high-quality flashcard questions in structured JSON format from provided text. You will strictly adhere to all formatting requirements and instructions regarding question quantity and type."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        log_prefix = f"[OpenAI Caller Chunk {chunk_info if is_chunked else 'MAIN_CALL'}]"
        print(f"{log_prefix} Sending request (type: {question_type_selected}). Text length: {len(text_content)}. Desired Qs: ~{num_desired_questions}.")
        openai_call_start_time = time.time()
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL_NAME,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.3, 
            # max_tokens parameter removed to let json_object mode try to fit output
        )
        openai_call_duration = time.time() - openai_call_start_time
        
        response_content_str = response.choices[0].message.content
        
        print(f"{log_prefix} Received response in {openai_call_duration:.2f}s. Length: {len(response_content_str)}")
        return response_content_str
    except openai.APIConnectionError as e:
        raise ConnectionError(f"Failed to connect to OpenAI: {e}")
    except openai.RateLimitError as e:
        raise Exception(f"OpenAI rate limit hit: {e}")
    except openai.APIStatusError as e: 
        raise Exception(f"OpenAI API error: Status {e.status_code} - {e.message}")
    except Exception as e:
        raise Exception(f"OpenAI API call failed: {str(e)}")

def image_to_base64_data_url(image_path):
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        if image_path.lower().endswith(('.heic', '.heif')): mime_type = 'image/heic'
        else: mime_type = 'image/png'
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:{mime_type};base64,{encoded_string}"

def get_questions_from_image_openai(image_file_path, question_type_selected):
    if not openai_client: raise ConnectionError("OpenAI client not configured.")
    base64_image = image_to_base64_data_url(image_file_path)
    type_specific_instructions = "" 
    mcq_options_field_example = ""  
    if question_type_selected == "MCQs":
        type_specific_instructions = "For MCQs: Question in 'question', array of 3-4 choices in 'options', correct choice text in 'answer'."
        mcq_options_field_example = '\n          "options": ["Choice 1", "Choice 2", "Choice 3", "Correct Choice"],'
    elif question_type_selected == "Fill-in-the-Blanks": type_specific_instructions = "For Fill-in-the-Blanks, 'question' uses '_____' for blanks, 'answer' is the filling."
    elif question_type_selected == "True or False": type_specific_instructions = "For True or False, 'question' is a statement, 'answer' is 'True' or 'False'."
    elif question_type_selected == "One-word Answer": type_specific_instructions = "For One-word Answer, 'answer' is a single significant word/short phrase."
    elif question_type_selected == "Short Answer": type_specific_instructions = "For Short Answer, 'answer' is a concise explanation (1-3 sentences)."

    json_structure_note = """Ensure "options" is array of strings ONLY for "MCQs"; else null/omitted. "source_page" must be present (null for images)."""
    prompt_messages = [{"role": "system", "content": "You are an AI assistant that analyzes images and generates structured JSON output for flashcards. Output MUST be a single JSON object."},
        {"role": "user", "content": [{"type": "text", "text": f"""Analyze the image and generate distinct "{question_type_selected}" questions.
Specific instructions for "{question_type_selected}": {type_specific_instructions}. Aim for 3-7 questions.
Required JSON Output Structure: {{ "questions": [ {{ "id": "unique_img_q_id_1", "question_type": "{question_type_selected}", "question": "...",{mcq_options_field_example} "answer": "...", "source_page": null }} ] }}
{json_structure_note} Each "id" must be unique."""},
                {"type": "image_url", "image_url": {"url": base64_image, "detail": "high"}},],}]
    try:
        print(f"[OpenAI Vision] Sending request for image Q&A (type: {question_type_selected}).")
        openai_call_start_time = time.time()
        response = openai_client.chat.completions.create(model=OPENAI_MODEL_NAME, messages=prompt_messages, max_tokens=1500)
        openai_call_duration = time.time() - openai_call_start_time
        response_content_str = response.choices[0].message.content
        cleaned_response_text = response_content_str.strip()
        if cleaned_response_text.startswith("```json"): cleaned_response_text = cleaned_response_text[7:]
        if cleaned_response_text.endswith("```"): cleaned_response_text = cleaned_response_text[:-3]
        cleaned_response_text = cleaned_response_text.strip()
        print(f"[OpenAI Vision] Received response in {openai_call_duration:.2f}s. Cleaned length: {len(cleaned_response_text)}")
        return cleaned_response_text
    except Exception as e:
        raise Exception(f"OpenAI Vision API call failed: {str(e)}")


def create_text_chunks_with_page_context(text_to_chunk_str, overall_pages_for_text_block, max_chars_per_chunk):
    chunks = []
    current_chunk_text = ""
    current_char_count = 0
    
    if not text_to_chunk_str: return []
    # Tokenize the input text_block_str into sentences. This needs nltk.sent_tokenize
    sentences_in_block = sent_tokenize(text_to_chunk_str)

    for sentence_text in sentences_in_block:
        sentence_text = sentence_text.strip()
        if not sentence_text:
            continue
        
        if current_char_count + len(sentence_text) + 1 > max_chars_per_chunk and current_chunk_text:
            # For each chunk, associate it with the broader page context of the original text block
            chunks.append({"text": current_chunk_text.strip(), 
                           "pages": overall_pages_for_text_block}) 
            current_chunk_text = ""
            current_char_count = 0
        
        current_chunk_text += sentence_text + " " 
        current_char_count += len(sentence_text) + 1

    if current_chunk_text.strip():
        chunks.append({"text": current_chunk_text.strip(), 
                       "pages": overall_pages_for_text_block})
    
    print(f"[CHUNKER] Created {len(chunks)} chunks. Max chars per chunk target: {max_chars_per_chunk}.")
    return chunks

@app.route('/api/generate-flashcards', methods=['POST'])
def generate_flashcards_route():
    overall_start_time = time.time()
    print(f"\n[APP_ROUTE] Request at {datetime.now().isoformat()} using OpenAI {OPENAI_MODEL_NAME}")

    if not openai_client: return jsonify({"error": "OpenAI client not configured."}), 503
    if 'file' not in request.files: return jsonify({"error": "No file part"}), 400
    uploaded_file = request.files['file']
    question_type = request.form.get('question_type')
    if not uploaded_file.filename: return jsonify({"error": "No selected file"}), 400
    if not question_type: return jsonify({"error": "Question type not specified"}), 400

    original_filename = secure_filename(uploaded_file.filename)
    _, file_extension = os.path.splitext(original_filename)
    file_extension = file_extension.lower()

    temp_file_path = None
    all_generated_questions = []

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension, prefix="openai_upload_") as temp_f:
            uploaded_file.save(temp_f.name)
            temp_file_path = temp_f.name
        print(f"[APP_ROUTE] File '{original_filename}' saved to '{temp_file_path}'. QType: '{question_type}'.")

        if file_extension == ".pdf":
            pdf_process_start_time = time.time()
            raw_text_by_page = [] 
            total_pdf_pages = 0
            with pdfplumber.open(temp_file_path) as pdf:
                total_pdf_pages = len(pdf.pages)
                for i, page_obj in enumerate(pdf.pages):
                    page_text_content = page_obj.extract_text()
                    if page_text_content and page_text_content.strip():
                        raw_text_by_page.append((page_text_content.strip(), i + 1)) 
            
            if not raw_text_by_page: return jsonify({"error": "No extractable text in PDF."}), 422
            print(f"[APP_ROUTE_PDF] Extracted text from {len(raw_text_by_page)} of {total_pdf_pages} pages.")

            # Call summarizer.py's process_text_for_qna
            # It returns: (best_summary_text_for_show, pages_for_best_summary_show, method_for_show, metrics_for_show, 
            #              full_filtered_text_from_pipeline, pages_for_full_filtered_text_openai)
            _best_summary_for_show, _pages_for_best_summary_show, _method_for_show, _metrics_for_show, \
            full_filtered_text_from_pipeline, pages_for_full_filtered_text_openai = \
                process_text_for_qna(raw_text_by_page, total_pdf_pages)
            
            if not full_filtered_text_from_pipeline:
                print("[APP_ROUTE_PDF_ERROR] Summarizer/Filter pipeline returned no full_filtered_text.")
                return jsonify({"error": "No content available after boilerplate filtering."}), 500
            
            num_meaningful_pages_for_prompt = len(pages_for_full_filtered_text_openai)
            
            # --- Decision: What text to send to OpenAI? ---
            text_to_send_to_openai = full_filtered_text_from_pipeline
            pages_for_openai_context = pages_for_full_filtered_text_openai
            
            # If the full filtered text is shorter than our preferred single-call limit, use it.
            # Otherwise, use the "best summary" (which is now targeted to be a large % of original).
            if len(full_filtered_text_from_pipeline) > OPENAI_INPUT_USE_FULL_TEXT_IF_SHORTER_THAN_CHARS:
                print(f"[APP_ROUTE_PDF] Full filtered text ({len(full_filtered_text_from_pipeline)} chars) is larger than preferred single-call limit ({OPENAI_INPUT_USE_FULL_TEXT_IF_SHORTER_THAN_CHARS} chars).")
                if _best_summary_for_show and len(_best_summary_for_show) > 0.05 * len(full_filtered_text_from_pipeline): # Ensure summary is not trivially short
                    print(f"  Using 'best evaluated summary' (method: {_method_for_show}, length: {len(_best_summary_for_show)} chars) instead.")
                    text_to_send_to_openai = _best_summary_for_show
                    pages_for_openai_context = _pages_for_best_summary_show
                    # Update meaningful pages for prompt if using summary's pages
                    num_meaningful_pages_for_prompt = len(pages_for_openai_context) if pages_for_openai_context else num_meaningful_pages_for_prompt
                else:
                    print(f"  'Best evaluated summary' is too short or empty. Proceeding with full filtered text (will be chunked if > chunk limit).")
            else:
                 print(f"[APP_ROUTE_PDF] Full filtered text ({len(full_filtered_text_from_pipeline)} chars) is within preferred limit. Using it directly.")


            if not text_to_send_to_openai.strip():
                 print("[APP_ROUTE_PDF_ERROR] No text content selected to send to OpenAI after decision logic.")
                 return jsonify({"error": "No text content available for Q&A generation after processing."}), 500

            pdf_text_prep_duration = time.time() - pdf_process_start_time
            print(f"[APP_ROUTE_PDF] PDF text extraction, filtering & summarizer 'show' run took {pdf_text_prep_duration:.2f}s.")
            print(f"[APP_ROUTE_PDF] Final text selected for OpenAI (length: {len(text_to_send_to_openai)} chars) from ~{num_meaningful_pages_for_prompt} effective pages. Associated pages: {pages_for_openai_context[:5]}... (if many)")

            # --- CHUNKING LOGIC for the chosen text_to_send_to_openai ---
            text_chunks_with_pages = create_text_chunks_with_page_context(
                text_to_send_to_openai,
                pages_for_openai_context, # Pass the page context for this block
                MAX_CHARS_PER_CHUNK_FOR_OPENAI # Use this for chunking chosen text
            )
            
            if not text_chunks_with_pages:
                 if text_to_send_to_openai.strip(): 
                     text_chunks_with_pages = [{"text": text_to_send_to_openai, "pages": pages_for_openai_context}]
                 else:
                    return jsonify({"error": "No text content available for chunking or Q&A."}), 500

            if len(text_chunks_with_pages) == 1:
                print("[APP_ROUTE_PDF] Sending single block/chunk to OpenAI.")
                chunk_data = text_chunks_with_pages[0]
                qna_json_string = get_questions_from_text_openai(
                    chunk_data["text"], question_type, chunk_data["pages"], 
                    num_meaningful_pages_for_prompt, is_chunked=False 
                )
                if qna_json_string:
                    try:
                        parsed_chunk = json.loads(qna_json_string)
                        if parsed_chunk and isinstance(parsed_chunk.get("questions"), list):
                            all_generated_questions.extend(parsed_chunk["questions"])
                    except Exception as e:
                        print(f"[APP_ROUTE_PDF] Error parsing single text response: {e}. Response: {qna_json_string[:500]}")
            else: 
                print(f"[APP_ROUTE_PDF] Sending {len(text_chunks_with_pages)} chunks to OpenAI in parallel (Max workers: {MAX_WORKERS_FOR_CHUNKING}).")
                with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS_FOR_CHUNKING) as executor:
                    future_to_chunk_index = {
                        executor.submit(
                            get_questions_from_text_openai,
                            chunk_data["text"], question_type, chunk_data["pages"],
                            num_meaningful_pages_for_prompt, True, f"{idx + 1}/{len(text_chunks_with_pages)}"
                        ): idx for idx, chunk_data in enumerate(text_chunks_with_pages)
                    }
                    for future in concurrent.futures.as_completed(future_to_chunk_index):
                        chunk_idx = future_to_chunk_index[future]
                        try:
                            chunk_qna_json_string = future.result()
                            if chunk_qna_json_string:
                                chunk_parsed_output = json.loads(chunk_qna_json_string)
                                if chunk_parsed_output and isinstance(chunk_parsed_output.get("questions"), list):
                                    all_generated_questions.extend(chunk_parsed_output["questions"])
                        except Exception as exc:
                            print(f"[APP_ROUTE_PDF] Chunk {chunk_idx + 1} generated an exception during OpenAI call: {exc}")
            print(f"[APP_ROUTE_PDF] Processed {len(text_chunks_with_pages)} chunks for PDF.")

        elif file_extension in [".png", ".jpg", ".jpeg", ".heic", ".heif", ".webp", ".gif", ".bmp"]:
            img_process_start_time = time.time()
            single_image_qna_json_string = get_questions_from_image_openai(temp_file_path, question_type)
            if single_image_qna_json_string:
                try:
                    parsed_output = json.loads(single_image_qna_json_string)
                    if parsed_output and isinstance(parsed_output.get("questions"), list):
                        all_generated_questions.extend(parsed_output["questions"])
                except Exception as e: print(f"[APP_ROUTE_IMG] Error parsing JSON from image Q&A: {e}")
            img_process_duration = time.time() - img_process_start_time
            print(f"[APP_ROUTE_IMG] Image Q&A with OpenAI took {img_process_duration:.2f}s.")
        else:
            return jsonify({"error": f"Unsupported file type: '{file_extension}'."}), 415
        
        json_parse_start_time = time.time()
        final_formatted_questions = []
        unique_q_texts = set() 
        for i, q_item_raw in enumerate(all_generated_questions):
            if isinstance(q_item_raw, dict) and "question" in q_item_raw and "answer" in q_item_raw:
                question_text_norm = q_item_raw["question"].strip().lower()
                if question_text_norm in unique_q_texts:
                    print(f"Skipping duplicate question: {question_text_norm[:50]}...")
                    continue
                unique_q_texts.add(question_text_norm)
                q_item_raw["id"] = q_item_raw.get("id", f"oa_q_final_{datetime.now().timestamp()}_{i}")
                q_item_raw["question_type"] = q_item_raw.get("question_type", question_type)
                raw_src_page = q_item_raw.get("source_page")
                if isinstance(raw_src_page, list): q_item_raw["source_page"] = ", ".join(map(str, raw_src_page))
                elif raw_src_page is not None: q_item_raw["source_page"] = str(raw_src_page)
                else: q_item_raw["source_page"] = None
                if q_item_raw["question_type"] == "MCQs":
                    if "options" not in q_item_raw or not isinstance(q_item_raw["options"], list): q_item_raw["options"] = None
                else: q_item_raw["options"] = q_item_raw.get("options") 
                final_formatted_questions.append(q_item_raw)
            else: print(f"Skipping malformed Q item during final aggregation: {q_item_raw}")
        json_parse_duration = time.time() - json_parse_start_time
        print(f"[APP_ROUTE] JSON parsing & final formatting took {json_parse_duration:.2f}s. Total unique questions: {len(final_formatted_questions)}")
        if not final_formatted_questions and all_generated_questions: return jsonify({"error": "AI data malformed post-aggregation."}), 500
        elif not final_formatted_questions: return jsonify({"questions": []}), 200
        return jsonify({"questions": final_formatted_questions}), 200
            
    except ConnectionError as e: return jsonify({"error": f"AI service connection error: {str(e)}"}), 503
    except openai.APIError as e: 
        print(f"OpenAI API Error in route: {e}")
        return jsonify({"error": f"OpenAI API service error: Status {e.status_code} - {e.message}"}), getattr(e, 'status_code', 500)
    except Exception as e: 
        print(f"Unexpected error in route: {e}")
        import traceback
        traceback.print_exc() 
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try: os.remove(temp_file_path); print(f"[APP_ROUTE] Cleaned temp: {temp_file_path}")
            except Exception as e_clean: print(f"Error cleaning temp file {temp_file_path}: {e_clean}")
        overall_duration = time.time() - overall_start_time
        print(f"[APP_ROUTE] Total request time: {overall_duration:.2f} seconds.")
        print("-" * 70)

if __name__ == '__main__':
    print("Starting Flask backend (using OpenAI GPT-4o with sample-based summarizer selection)...")
    if not openai_client: print("CRITICAL: OpenAI client FAILED init.")
    else: print(f"OpenAI client OK. Model: '{OPENAI_MODEL_NAME}'.")
    if OPENAI_API_KEY == "YOUR_ACTUAL_OPENAI_API_KEY_PLACEHOLDER" or not OPENAI_API_KEY : print("WARNING: OpenAI API Key placeholder.")
    else: print(f"Using OpenAI API key: {OPENAI_API_KEY[:10]}...{OPENAI_API_KEY[-4:]}")
    app.run(debug=True, host='0.0.0.0', port=5000)