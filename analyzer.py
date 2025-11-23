import google.generativeai as genai
import json
import typing_extensions as typing
from pypdf import PdfReader
from config import API_KEY, MODEL_NAME, SYLLABUS_PROMPT

if API_KEY:
    genai.configure(api_key=API_KEY)

# Strict JSON Schema
class Topic(typing.TypedDict):
    """Schema for a single study topic."""
    topic_name: str
    difficulty: str
    estimated_hours: int

class SyllabusPlan(typing.TypedDict):
    """Schema for the overall syllabus plan."""
    subject: str
    topics: list[Topic]

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts text content from a PDF file.

    Args:
        pdf_path (str): The file path to the PDF.

    Returns:
        str: The extracted text content, or an error message if extraction fails.
    """
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

import time

def repair_json(text: str) -> str:
    """Attempts to repair common JSON formatting errors from LLM output."""
    text = text.strip()
    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def analyze_syllabus(pdf_path: str) -> dict:
    """
    Analyzes a syllabus PDF using Google Gemini to extract topics and difficulty.
    Includes retry logic and JSON repair.
    """
    raw_text = extract_text_from_pdf(pdf_path)
    
    # Check for truncation
    if len(raw_text) > 30000:
        print(f"⚠️ Warning: Syllabus is too long ({len(raw_text)} chars). Truncating the end to save costs.")
        
    clean_text = raw_text[:30000] # Context limit safety
    
    model = genai.GenerativeModel(MODEL_NAME)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = model.generate_content(
                f"{SYLLABUS_PROMPT}\n\nTEXT:\n{clean_text}",
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=SyllabusPlan
                )
            )
            json_text = repair_json(result.text)
            return json.loads(json_text)
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise RuntimeError(f"Failed to analyze syllabus after {max_retries} attempts.")
            time.sleep(1) # Wait a bit before retrying
    return {}

def get_strategy_tips(topic_name: str, difficulty: str) -> str:
    """
    Generates a custom study strategy for a specific topic using AI.

    Args:
        topic_name (str): The name of the topic to study.
        difficulty (str): The difficulty level of the topic.

    Returns:
        str: A string containing the strategy tips (Concept, Action, Trap).
    """
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = f"""
    Give me a brutal, effective micro-strategy to study '{topic_name}' (Difficulty: {difficulty}).
    Provide 3 bullet points:
    1. The Concept (Analogy).
    2. The Action (What code to write).
    3. The Trap (Common mistake).
    Keep it under 100 words.
    """
    response = model.generate_content(prompt)
    return response.text

def get_daily_briefing(tasks_list: str) -> str:
    """
    Generates a motivational daily briefing based on the day's tasks.

    Args:
        tasks_list (str): A string representation or list of tasks for the day.

    Returns:
        str: A 2-sentence motivational message.
    """
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = f"I have these tasks: {tasks_list}. Give me a 2-sentence battle plan to motivate me."
    response = model.generate_content(prompt)
    return response.text
