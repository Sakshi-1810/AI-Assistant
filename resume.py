import pdfplumber
from docx import Document
import os
from dotenv import load_dotenv
import google.generativeai as genai
import json

# Load API key
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extract_text_from_resume(filepath):
    ext = filepath.rsplit('.', 1)[-1].lower()
    text = ""
    try:
        if ext == 'pdf':
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
        elif ext == 'docx':
            doc = Document(filepath)
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif ext == 'doc':
            text += "DOC format not supported without external tools."
    except Exception as e:
        text = f"Error reading resume: {str(e)}"
    return text.strip()


def extract_resume_details(resume_text):
    """Returns structured resume data"""
    prompt = f"""
You are a resume parser. Extract the following fields in valid JSON:

{{
  "name": "",
  "email": "",
  "phone": "",
  "location": "",
  "linkedin": "",
  "github": "",
  "skills": [],
  "education": [{{"degree": "", "institution": "", "year": ""}}],
  "work_experience": [{{"job_title": "", "company": "", "duration": ""}}],
  "certifications": []
}}

Resume:
{resume_text}

Only return valid JSON.
"""
    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    response = model.generate_content(prompt)
    try:
        text = response.text.strip()
        json_part = text[text.find("{"):text.rfind("}")+1]
        json_part = json_part.replace("\u2013", "-").replace("–", "-")
        return json.loads(json_part)
    except Exception as e:
        print("⚠️ Failed to extract JSON:", e)
        return {"error": "Resume parsing failed."}


def match_jobs(resume_text, resume_skills):
    """Matches jobs using resume skills"""
    try:
        with open("jobs.json", "r") as f:
            job_data = json.load(f)

        prompt = f"""
You are an AI job advisor.

Resume Summary:
{resume_text}

Skills:
{', '.join(resume_skills)}

Here are job openings:
{json.dumps(job_data, indent=2)}

Suggest only the most relevant jobs based on skill match and explain briefly why.

Output:
"""
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        return f"Error matching jobs: {e}"

def get_latest_resume_path(folder="uploads"):
    files = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith((".pdf", ".docx"))
    ]
    if not files:
        raise FileNotFoundError("No PDF or DOCX resumes found in uploads folder.")
    return max(files, key=os.path.getmtime)


if __name__ == "__main__":
    try:
        path = get_latest_resume_path()
        print(f"📄 Using latest resume file: {path}\n")

        resume_text = extract_text_from_resume(path)
        resume_details = extract_resume_details(resume_text)

        print("🎯 Resume Key Details (JSON):\n")
        print(json.dumps(resume_details, indent=2))

    except Exception as e:
        print(f"❌ Error: {e}")

