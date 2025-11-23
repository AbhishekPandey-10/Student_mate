import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration
API_KEY = os.getenv("GEMINI_API_KEY")  # Google Gemini API Key
MODEL_NAME = "gemini-flash-latest"        # Model version to use

# Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "study_agent")

# Logic Settings
REVISION_BUFFER_DAYS = 10  # Target: Finish syllabus 10 days before exam to allow for revision
MIN_STUDY_DAYS = 1         # Absolute minimum learning window allowed

# Prompts
# Prompt used for analyzing syllabus content
SYLLABUS_PROMPT = """
Analyze the following syllabus text. 
1. Break it down into logical study topics.
2. Rate difficulty (Easy/Medium/Hard) based on a standard CS curriculum.
3. Estimate hours needed for a beginner.
Return valid JSON only using the defined schema.
"""
