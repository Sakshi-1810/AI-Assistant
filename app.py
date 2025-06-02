from flask import Flask, request, render_template, redirect, flash, jsonify
from flask_session import Session
import requests
from bs4 import BeautifulSoup
import os
import json
from resume import extract_text_from_resume, extract_resume_details, match_jobs
from dotenv import load_dotenv
import google.generativeai as genai
from flask import request, jsonify
import re


app = Flask(__name__)
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


DOMAIN = "https://webanixsolutions.com"
suggestion_keywords = []


def get_sitemap_url():
    test_urls = [
        f"{DOMAIN.rstrip('/')}/sitemap.xml",
        f"{DOMAIN.rstrip('/')}/sitemap_index.xml"
    ]
    for url in test_urls:
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                return url
        except Exception:
            continue
    return None

def fetch_sitemap_urls(sitemap_url):
    try:
        response = requests.get(sitemap_url)
        soup = BeautifulSoup(response.content, "xml")
        return [loc.text for loc in soup.find_all("loc")]
    except Exception as e:
        print(f"Error fetching sitemap: {e}")
        return []
    
def filter_urls_with_gemini(question, all_urls):
    url_text = "\n".join(all_urls)
    prompt = f"""
You are an intelligent assistant. A user has a question about a website. Below is the full list of sitemap URLs.
Your job is to select only the most relevant page URLs that should be used to answer the user's question.

💡 Hint:
Even if a URL has a query string like `?career=true` or `?job=openings`, include it if it looks relevant.
User Question:
{question}

Sitemap URLs:
{url_text}

Return the relevant URLs only, each on a new line, without extra explanation.
"""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        response = model.generate_content(prompt)
        return [url.strip() for url in response.text.strip().splitlines() if url.strip().startswith("http")]
    except Exception as e:
        print(f"Gemini filtering error: {e}")
        return []

def scrape_text_from_urls(urls):
    all_text = ""
    for url in urls:
        try:
            res = requests.get(url, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")

            content = '\n'.join([el.get_text(strip=True) for el in soup.find_all(['p', 'h1', 'h2', 'h3','li'])])

            links = []
            for a in soup.find_all("a", href=True):
                link_href = a["href"]
                link_text = a.get_text(strip=True)

                if not link_text:
                    if a.img and a.img.get("alt"):
                        link_text = a.img["alt"]
                    elif a.get("title"):
                        link_text = a["title"]
                    elif "linkedin" in link_href:
                        link_text = "LinkedIn"
                    elif "instagram" in link_href:
                        link_text = "Instagram"
                    elif "facebook" in link_href:
                        link_text = "Facebook"
                    else:
                        link_text = "[Icon Link]"

                if link_href.startswith("/"):
                    link_href = requests.compat.urljoin(url, link_href)

                links.append(f"- {link_text} → {link_href}")

            links_section = "\nRelevant Links:\n" + "\n".join(links) if links else ""
            all_text += f"\n### {url} ###\n{content}{links_section}\n"

        except Exception as e:
            print(f"Error scraping {url}: {e}")
    return all_text


def ask_gemini(question, context):
    prompt = f"""
You are an AI assistant trained on this website's content. Answer clearly and concisely.

Your primary objective is to convert visitors into qualified leads or customers by providing tailored recommendations, showcasing value propositions, and guiding users through the buyer journey.

Here's what you must always do:

Understand the full scope of services/products offered via the sitemap and content structure.

Use confident, benefit-oriented language to highlight how our offerings solve user problems.

Ask intelligent, low-friction questions to identify the visitor’s needs and guide them to the right solution.

Recommend the most relevant product, service, or contact action (e.g. booking a demo, requesting a quote).

Be proactive: suggest next steps even if the visitor is unsure what they want.

if answer contain multiple points ,then give answer in number sequence. 
If ques is about career ,job ,apply ,resume and technolgies ,answer from the career=true page.

Context:
{context}

User Question:
{question}

Answer:
"""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generating response: {e}"

chat_history = []

@app.route("/", methods=["GET", "POST"])
def index():
    global chat_history
    if request.method == "POST":
        if request.form.get("action") == "clear":
            chat_history = []
        else:
            question = request.form.get("question")
            if question:
                try:
                    sitemap_url = get_sitemap_url()
                    if not sitemap_url:
                        raise Exception("No valid sitemap found for domain.")

                    all_urls = fetch_sitemap_urls(sitemap_url)
                    career_keywords = ["career", "job", "technology", "technologies"]
                    career_page = f"{DOMAIN.rstrip('/')}/careers"
                    if any(keyword in question.lower() for keyword in career_keywords):
                       all_urls.append(career_page)
                       
                    apply_keywords_regex = r"\b(apply|resume|interested|want to work|submit resume)\b.*\b(job|role|position|career|profile)?\b"

                    if re.search(apply_keywords_regex, question, re.IGNORECASE):
                        response = "Please upload your resume using the *Explore Career Options* link below so we can help you apply for the right job!"
                        chat_history.append(("Assistant", response))
                        return render_template("index.html", history=chat_history)    

                    relevant_urls = filter_urls_with_gemini(question, all_urls)
                    scraped_context = scrape_text_from_urls(relevant_urls)
                    answer = ask_gemini(question, scraped_context)

                    chat_history.append(("User", question))
                    chat_history.append(("Assistant", answer))
                except Exception as e:
                    chat_history.append(("Error", str(e)))
    return render_template("index.html", history=chat_history)

@app.route("/careers", methods=["GET", "POST"])
def careers():
    career_suggestions = None
    uploaded = False

    if request.method == 'POST':
        file = request.files.get('resume')
        if file and allowed_file(file.filename):
            path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(path)
            uploaded = True
            flash("Resume uploaded successfully!")

            resume_text = extract_text_from_resume(path)
            resume_info = extract_resume_details(resume_text)

            if "skills" in resume_info and isinstance(resume_info["skills"], list):
                career_suggestions = match_jobs(resume_text, resume_info["skills"])
            else:
                career_suggestions = "⚠️ Could not find skills in resume. Try again."
        else:
            flash("Invalid file. Please upload PDF, DOC, or DOCX.")

    return render_template("careers.html", uploaded=uploaded, suggestions=career_suggestions)

@app.route("/suggest")
def suggest():
    query = request.args.get("q", "").strip()
    if not query or len(query) < 10:
        return jsonify([])

    prompt = f"""
You are a helpful autocomplete assistant for the website: {DOMAIN}.

The user has started typing: "{query}"

Your task is to return 5 smart and concise autocomplete-style suggestions based ONLY on the website's topics, structure, sitemap, and common queries.

✔️ Suggestions must:
- Be relevant to the site's services, products, careers, about, contact, etc.
- Sound like something a user would search or click
- Be short and informative (max 7-8 words)
- NOT include irrelevant or generic internet phrases

❌ Avoid:
- Generic AI suggestions (e.g., "What is AI?")
- Suggestions that are not part of the domain
- Anything unrelated to the website

Return only 5 suggestions, one per line, no explanations.

Example:
User types: "serv"
Suggestions:
- Services offered by the company
- Top services for businesses
- Web development services
- Mobile app solutions
- Services provided by company

User types: "{query}"
Suggestions:
"""


    try:
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        response = model.generate_content(prompt)
        suggestions = [
            line.strip() for line in response.text.splitlines()
            if line.strip()
        ]
        return jsonify(suggestions[:3])
    except Exception as e:
        print("Suggestion error:", e)
        return jsonify([])


if __name__ == "__main__":
    app.run(debug=True)