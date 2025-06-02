# AI Assistant

This project is a local AI-powered resume analysis tool. It uses the **Gemini API** to:

- 📝 Extract structured key details from resumes (Name, Email, Skills, Experience, etc.)
- 🎯 Suggest career options that match both the user's skills and Webanix's technologies

---

## 📁 Folder Structure

```
webanix-resume-ai/
├── uploads/                  # Put your resume files (.pdf or .docx) here
├── analyze_webanix_resume.py # Main Python script (terminal-based)
├── README.md
```

---

## 🚀 Requirements

- Python 3.8+
- Google Gemini API access and key
- Internet connection (to scrape the Webanix website and access Gemini)

### 📦 Install Python dependencies:

```bash
pip install pdfplumber python-docx requests beautifulsoup4 google-generativeai
```

---

## 🧠 Run the Tool

Place your latest resume in the `uploads/` folder (as `.pdf` or `.docx`).

Then run:

```bash
python analyze_webanix_resume.py
```

### ✅ Output:
- 📋 JSON with key resume details (Name, Skills, Experience, etc.)
- 🎯 AI-suggested job roles based on Webanix's tech stack

---

## 💡 How It Works

1. The script reads the latest resume from the `uploads` folder.
2. Extracts text using `pdfplumber` or `python-docx`.
3. Sends it to the **Gemini model** via API with 2 prompts:
   - One to extract structured JSON resume data
   - One to suggest relevant job roles (based on Webanix’s tech stack)

---

## 🛠️ Technologies Used by Webanix (as per careers page)

```text
React.js, Angular, Node.js, Python, React Native, Android, PHP, DevOps,
.NET, SEO, Social Media Marketing, Lead Generation, Business Development, Customer Success
```

The job suggestions only come from this stack.

---

## 🧪 Example Resume Paths

Put files like:
- `uploads/john_resume.pdf`
- `uploads/sample_resume.docx`

Only the **latest file** (by time) will be analyzed.

---

## 📞 Support
Need help? Reach out via your developer channel or contact support.

---

## 📄 License
MIT License — free to use, modify, and share.
