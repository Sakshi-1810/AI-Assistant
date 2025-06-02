import os
import json
import requests
import docx2txt
import PyPDF2

UPLOADS_DIR = "uploads"  # Your Flask uploads folder

def get_latest_resume_path(folder):
    """Get the most recently modified PDF or DOCX file."""
    files = [os.path.join(folder, f) for f in os.listdir(folder)
             if f.lower().endswith((".pdf", ".docx"))]

    if not files:
        raise FileNotFoundError("No .pdf or .docx files found in uploads folder.")

    # Sort by modification time
    latest = max(files, key=os.path.getmtime)
    return latest

def extract_text_from_file(filepath):
    """Extract text content from PDF or DOCX file."""
    if filepath.endswith('.pdf'):
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            return ''.join(page.extract_text() for page in reader.pages if page.extract_text())

    elif filepath.endswith('.docx'):
        return docx2txt.process(filepath)

    else:
        raise ValueError("Unsupported file format. Use .pdf or .docx")

def query_mistral_for_json(text):
    """Send the extracted resume text to Mistral and return parsed JSON."""
    prompt = f"""
You are a resume parser. Read the resume below and extract the following fields in clean JSON format:

- name
- email
- phone
- location
- education: list of objects with degree, institution, and passing year 
- skills: list of skills
- work_experience: list of objects with job_title, company, and duration
- certifications: list of certificates
- linkedin: LinkedIn profile link (if available)
- github: GitHub profile link (if available)

Only return valid JSON.

Resume:
{text}

Extracted JSON:
""".strip()

    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False
            }
        )

        result_text = res.json().get("response", "").strip()

        # Extract only the JSON part
        json_start = result_text.find("{")
        json_end = result_text.rfind("}") + 1
        json_block = result_text[json_start:json_end]
        json_block = json_block.replace("\u2013", "-").replace("–", "-")

        return json.loads(json_block)

    except json.JSONDecodeError:
        print("⚠️ Mistral did not return valid JSON. Raw output:\n")
        print(result_text)
        return None

    except Exception as e:
        print(f"⚠️ Error querying Mistral: {e}")
        return None

def main():
    try:
        resume_path = get_latest_resume_path(UPLOADS_DIR)
        print(f"📄 Using latest resume file: {resume_path}")

        text = extract_text_from_file(resume_path)
        extracted = query_mistral_for_json(text)

        if extracted:
            print("\n✅ Extracted Resume Details:\n")
            print(json.dumps(extracted, indent=4))
        else:
            print("⚠️ No valid JSON could be extracted from the resume.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
