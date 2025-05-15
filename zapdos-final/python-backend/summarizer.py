import nltk
from nltk.tokenize import sent_tokenize
import re
import time

# Sumy (imports remain the same)
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer as SumyTokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.summarizers.luhn import LuhnSummarizer
from sumy.summarizers.text_rank import TextRankSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words

from rouge_score import rouge_scorer
import textstat

LANGUAGE = "english"
# For the final "best summary" selected by metrics (this is what app.py might use if full text is too long)
TARGET_SUMMARY_SENTENCE_COUNT_RATIO = 0.60 
MIN_SENTENCES_FOR_SUMMARY = 10 
MAX_SENTENCES_FOR_SUMMARY = 150 # Cap for the "best summary" if 60% is still too many sentences

try:
    nltk.data.find('tokenizers/punkt')
except nltk.downloader.DownloadError:
    nltk.download('punkt', quiet=True)
try:
    nltk.data.find('corpora/stopwords')
except nltk.downloader.DownloadError:
    nltk.download('stopwords', quiet=True)

# --- Boilerplate Detection Keywords/Patterns ---
BOILERPLATE_HEADINGS = [
    r"table of contents", r"contents", r"preface", r"foreword", r"acknowledgements?",
    r"dedication", r"introduction", r"executive summary", r"abstract", r"index",
    r"bibliography", r"references", r"glossary", r"appendix", r"about the author(s)?",
    r"author bio(s)?", r"notes to the reader", r"list of figures", r"list of tables", r"errata"
]
HEADING_PATTERN = re.compile(r"^\s*(" + "|".join(BOILERPLATE_HEADINGS) + r")\s*(\(?\d{0,4}\)?)?\s*$", re.IGNORECASE | re.MULTILINE)
TOC_INDEX_LINE_PATTERN = re.compile(r"^(.*?)\s*[._\s]+\s*([ivxlcdm\d]+)\s*$", re.IGNORECASE | re.MULTILINE)


def is_likely_boilerplate_page(page_text_content, page_number, total_pages):
    """
    Heuristically determines if a page is likely boilerplate.
    """
    text_lower = page_text_content.lower()
    first_few_lines = "\n".join(page_text_content.splitlines()[:5])
    if HEADING_PATTERN.search(first_few_lines):
        for heading_keyword in BOILERPLATE_HEADINGS:
            if re.search(r"^\s*" + re.escape(heading_keyword) + r"\s*$", first_few_lines, re.IGNORECASE | re.MULTILINE):
                if heading_keyword.lower() in ["introduction", "executive summary", "abstract"] and \
                   (page_number > total_pages * 0.10 and page_number < total_pages * 0.90) and \
                   len(page_text_content.split()) > 200: 
                    continue
                # print(f"[BOILERPLATE_FILTER] Page {page_number}: Filtered by heading '{heading_keyword}'.")
                return True
    lines = page_text_content.splitlines()
    if len(lines) > 4:
        toc_index_line_matches = sum(1 for line in lines if TOC_INDEX_LINE_PATTERN.search(line))
        if toc_index_line_matches / len(lines) > 0.4: # A bit more lenient if many lines look like ToC
            # print(f"[BOILERPLATE_FILTER] Page {page_number}: Filtered by ToC/Index pattern.")
            return True
    word_count = len(page_text_content.split())
    # Check first 5% or last 5% of pages if they are also short
    if (page_number <= max(1, int(total_pages * 0.05)) or \
        page_number >= total_pages - max(0, int(total_pages * 0.05)-1)) and \
        word_count < 150 : 
        for keyword in ["index", "references", "bibliography", "about the author", "glossary", "contents", "figure captions", "table captions", "acknowledgements"]: # Added more common end/front matter
             if keyword in text_lower:
                # print(f"[BOILERPLATE_FILTER] Page {page_number}: Filtered by position, low word count, and keyword '{keyword}'.")
                return True
    for keyword in ["preface", "foreword", "dedication", "author bio", "about the author", "notes to the reader", "copyright information", "isbn"]: # More specific front/back keywords
        if keyword in "\n".join(page_text_content.splitlines()[:15]).lower(): # Check more lines at top
            # print(f"[BOILERPLATE_FILTER] Page {page_number}: Filtered by strong keyword '{keyword}' near top.")
            return True
    return False

def preprocess_text_for_sumy(text):
    text = re.sub(r'\n\s*\n', '\n', text) 
    text = re.sub(r'[ \t]+', ' ', text)    
    return text.strip()

def get_sumy_summary(full_text, summarizer_type_str, target_sentence_count):
    parser = PlaintextParser.from_string(full_text, SumyTokenizer(LANGUAGE))
    stemmer = Stemmer(LANGUAGE)
    if summarizer_type_str == 'lexrank': summarizer_instance = LexRankSummarizer(stemmer)
    elif summarizer_type_str == 'luhn': summarizer_instance = LuhnSummarizer(stemmer)
    elif summarizer_type_str == 'lsa': summarizer_instance = LsaSummarizer(stemmer)
    elif summarizer_type_str == 'textrank': summarizer_instance = TextRankSummarizer(stemmer)
    else: raise ValueError(f"Unsupported summarizer type: {summarizer_type_str}")
    summarizer_instance.stop_words = get_stop_words(LANGUAGE)
    actual_target_count = max(1, target_sentence_count)
    summary_sentence_objects = summarizer_instance(parser.document, actual_target_count)
    return [str(s).strip() for s in summary_sentence_objects if str(s).strip()]

def calculate_rouge_scores(hypothesis_str, reference_str):
    if not hypothesis_str.strip() or not reference_str.strip(): return {'rouge1': 0, 'rouge2': 0, 'rougeL': 0}
    scorer_obj = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    scores_val = scorer_obj.score(reference_str, hypothesis_str)
    return {'rouge1': scores_val['rouge1'].fmeasure, 'rouge2': scores_val['rouge2'].fmeasure, 'rougeL': scores_val['rougeL'].fmeasure}

def calculate_all_metrics(summary_text_str, original_full_text_str):
    if not summary_text_str.strip():
        return {'rouge_scores': {'rouge1': 0, 'rouge2': 0, 'rougeL': 0}, 'compression_ratio': 1.0, 'readability_score': 0, 'f1_score_rougeL': 0, 'summary_sentence_count': 0}
    if not original_full_text_str.strip(): original_full_text_str = "." 

    rouge_scores_val = calculate_rouge_scores(summary_text_str, original_full_text_str)
    original_len = len(original_full_text_str); summary_len = len(summary_text_str)
    compression_ratio_val = summary_len / original_len if original_len > 0 else 1.0
    try: readability_score_val = textstat.flesch_reading_ease(summary_text_str)
    except: readability_score_val = 0 
    f1_score_val = rouge_scores_val['rougeL']
    summary_sentence_count_val = len(sent_tokenize(summary_text_str))
    return {'rouge_scores': rouge_scores_val, 'compression_ratio': compression_ratio_val, 'readability_score': readability_score_val, 'f1_score_rougeL': f1_score_val, 'summary_sentence_count': summary_sentence_count_val}

def map_summary_sentences_to_pages(summary_sentences_list, original_sentences_with_pages_metadata):
    summary_page_numbers_found = set()
    original_sents_lookup = {s_meta['text'].lower().strip(): s_meta['page'] for s_meta in original_sentences_with_pages_metadata}
    for summ_sent_str in summary_sentences_list:
        clean_summ_sent = summ_sent_str.strip().lower()
        if clean_summ_sent in original_sents_lookup:
            summary_page_numbers_found.add(original_sents_lookup[clean_summ_sent])
        # else:
            # print(f"[PAGE_MAP_DEBUG] Summary sentence not directly mapped: '{summ_sent_str[:30]}...'")
    return sorted(list(summary_page_numbers_found))

def process_text_for_qna(pdf_text_by_page_raw, total_pages_in_pdf):
    pipeline_start_time = time.time()
    print("\n[SUMMARIZER_PIPELINE] Initializing: Boilerplate removal & Multi-Summarizer Evaluation...")

    if not pdf_text_by_page_raw:
        print("[SUMMARIZER_PIPELINE] No raw text provided from PDF.")
        return "", [], "N/A", None, "", [] 

    content_text_with_pages = [] 
    print("[SUMMARIZER_PIPELINE] Filtering boilerplate content (REAL)...")
    for raw_page_text, page_num in pdf_text_by_page_raw:
        if is_likely_boilerplate_page(raw_page_text, page_num, total_pages_in_pdf):
            continue
        content_text_with_pages.append((raw_page_text, page_num))
    
    if not content_text_with_pages:
        print("[SUMMARIZER_PIPELINE] All pages filtered as boilerplate. Using first raw page as fallback.")
        if pdf_text_by_page_raw: 
            first_page_text, first_page_num = pdf_text_by_page_raw[0]
            # Create metadata for this single fallback page
            sents_meta = [{"text": s.strip(), "page": first_page_num} for s in sent_tokenize(first_page_text) if s.strip()]
            return first_page_text, [first_page_num], "Fallback (First Page Raw)", {}, first_page_text, [first_page_num]
        else:
            return "", [], "N/A", None, "", []

    original_sentences_metadata_filtered = [] 
    full_filtered_text_concatenated = ""
    pages_in_full_filtered_text = set()

    for text_content_item, page_num_item in content_text_with_pages:
        page_sents_list = sent_tokenize(text_content_item)
        for sent_str_item in page_sents_list:
            clean_sent_item = sent_str_item.strip()
            if clean_sent_item: 
                original_sentences_metadata_filtered.append({"text": clean_sent_item, "page": page_num_item})
        full_filtered_text_concatenated += text_content_item + "\n"
        pages_in_full_filtered_text.add(page_num_item)
    
    full_filtered_text_concatenated = preprocess_text_for_sumy(full_filtered_text_concatenated)
    final_pages_for_full_filtered_text = sorted(list(pages_in_full_filtered_text))

    if not original_sentences_metadata_filtered or not full_filtered_text_concatenated.strip():
        print("[SUMMARIZER_PIPELINE] No valid sentences after filtering for summarization.")
        # Still return the (empty) full_filtered_text and its pages
        return "", [], "N/A (No sentences post-filter)", None, full_filtered_text_concatenated, final_pages_for_full_filtered_text

    original_total_sentences_count = len(original_sentences_metadata_filtered)
    # Target for each of the 4 evaluated summaries
    target_sents_for_evaluation_summaries = max(MIN_SENTENCES_FOR_SUMMARY, 
                                      min(MAX_SENTENCES_FOR_SUMMARY, # Use the higher cap here
                                          int(original_total_sentences_count * TARGET_SUMMARY_SENTENCE_COUNT_RATIO)))
    
    print(f"[SUMMARIZER_PIPELINE] Filtered content: {original_total_sentences_count} sentences ({len(full_filtered_text_concatenated)} chars). Target for each evaluated summary: {target_sents_for_evaluation_summaries} sentences (aiming for ~60% of original).")

    summarizer_methods_to_eval = ['lsa', 'lexrank', 'luhn', 'textrank']
    all_summaries_data = []
    all_methods_metrics_log = {}

    for method_name_str in summarizer_methods_to_eval:
        method_start_time = time.time()
        print(f"[SUMMARIZER_PIPELINE] Evaluating: {method_name_str.upper()}")
        try:
            summary_sentences_list_val = get_sumy_summary(full_filtered_text_concatenated, method_name_str, target_sents_for_evaluation_summaries)
            current_summary_text = " ".join(summary_sentences_list_val)

            metrics_data = calculate_all_metrics(current_summary_text, full_filtered_text_concatenated)
            summary_pages_found = []
            if current_summary_text.strip():
                summary_pages_found = map_summary_sentences_to_pages(summary_sentences_list_val, original_sentences_metadata_filtered)
                if not summary_pages_found and content_text_with_pages: 
                    summary_pages_found = [content_text_with_pages[0][1]] 
            
            all_methods_metrics_log[method_name_str] = metrics_data
            all_summaries_data.append({
                'method': method_name_str,
                'summary_text': current_summary_text,
                'page_numbers': summary_pages_found,
                'metrics': metrics_data
            })
            method_time_taken = time.time() - method_start_time
            print(f"  {method_name_str.upper()} generated summary (length: {len(current_summary_text)} chars) and metrics in {method_time_taken:.2f}s. ROUGE-L F1: {metrics_data['f1_score_rougeL']:.3f}, Readability: {metrics_data['readability_score']:.1f}, Pages: {summary_pages_found}")

        except Exception as e_sum:
            print(f"  Error during {method_name_str} summarization/metrics: {e_sum}")
            metrics_placeholder = calculate_all_metrics("", full_filtered_text_concatenated)
            all_methods_metrics_log[method_name_str] = metrics_placeholder
            all_summaries_data.append({'method': method_name_str, 'summary_text': "", 'page_numbers': [], 'metrics': metrics_placeholder, 'overall_score': -float('inf')})

    if not any(s_data['summary_text'] for s_data in all_summaries_data):
        print("[SUMMARIZER_PIPELINE] No summaries were generated by any method. Returning full filtered text.")
        return full_filtered_text_concatenated, final_pages_for_full_filtered_text, "Fallback (Full Filtered)", all_methods_metrics_log, full_filtered_text_concatenated, final_pages_for_full_filtered_text

    score_weights = { 'rougeL': 0.40, 'readability': 0.30, 'compression_effectiveness': 0.30 } 

    for summary_obj in all_summaries_data:
        # ... (scoring logic remains same) ...
        if 'overall_score' in summary_obj and summary_obj['overall_score'] == -float('inf'): continue
        if not summary_obj['summary_text']:
            summary_obj['overall_score'] = -float('inf')
            if summary_obj['method'] in all_methods_metrics_log: all_methods_metrics_log[summary_obj['method']]['overall_score'] = -float('inf')
            else: all_methods_metrics_log[summary_obj['method']] = {'overall_score': -float('inf')}
            continue
        m = summary_obj['metrics']
        normalized_readability_score = max(0, min(100, m['readability_score'])) / 100.0
        compression_effectiveness_score = max(0, 1.0 - m['compression_ratio'] if m['compression_ratio'] <= 1.0 else -0.5) 
        calculated_score = (m['rouge_scores'].get('rougeL',0) * score_weights['rougeL'] + normalized_readability_score * score_weights['readability'] + compression_effectiveness_score * score_weights['compression_effectiveness'])
        summary_obj['overall_score'] = calculated_score
        if summary_obj['method'] in all_methods_metrics_log: all_methods_metrics_log[summary_obj['method']]['overall_score'] = calculated_score
        print(f"  Overall Score for {summary_obj['method'].upper()}: {calculated_score:.4f}")
        
    valid_summaries_for_show = [s for s in all_summaries_data if 'overall_score' in s and s['overall_score'] > -float('inf') and s['summary_text']]

    best_summary_object_for_show = None
    if valid_summaries_for_show:
        best_summary_object_for_show = max(valid_summaries_for_show, key=lambda item: item['overall_score'])
    
    pipeline_time_taken = time.time() - pipeline_start_time
    
    # Determine the text and pages to be returned for LLM processing
    if best_summary_object_for_show:
        text_for_llm = best_summary_object_for_show['summary_text']
        pages_for_llm = best_summary_object_for_show['page_numbers']
        method_chosen = best_summary_object_for_show['method']
        print(f"[SUMMARIZER_PIPELINE] Best method (for LLM input): {method_chosen.upper()} with score {best_summary_object_for_show['overall_score']:.4f}.")
    else: # Fallback if no valid summary was chosen by metrics
        print("[SUMMARIZER_PIPELINE] No valid 'best' summary found. Using full filtered text for LLM.")
        text_for_llm = full_filtered_text_concatenated
        pages_for_llm = final_pages_for_full_filtered_text
        method_chosen = "Fallback (Full Filtered Text)"
        
    print(f"[SUMMARIZER_PIPELINE] Summarization pipeline completed in {pipeline_time_taken:.2f} seconds.")
    
    return (text_for_llm, 
            pages_for_llm, 
            method_chosen, # This is the method whose summary is being returned for LLM
            all_methods_metrics_log, # This contains metrics for all evaluated methods
            full_filtered_text_concatenated, # Always return this for app.py to potentially use
            final_pages_for_full_filtered_text # And its pages
           )