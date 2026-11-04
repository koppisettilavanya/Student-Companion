# AI Student Companion - Intelligent Academic & Career Assistant

A full-stack, production-grade AI Student Companion web application powered by **Python Django**, **Groq Ultra-Fast LPU Inference (Official Python SDK)**, **SQLite**, and modern **Vanilla HTML5/CSS3/JavaScript**.

---

## ⚡ Tech Stack

- **Backend:** Python Django 4.2+
- **Frontend:** Pure HTML5, CSS3, Vanilla JavaScript (No React, Node.js, or frontend build frameworks)
- **AI Integration:** Official `groq` Python SDK (`qwen/qwen3.8-27b`, `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `allam-2-7b`, `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`)
- **Document & OCR Parsing:** `pypdf`, `python-docx`, `Pillow`, `pytesseract`
- **Database:** SQLite3 with Django ORM
- **Markdown & Code Highlighting:** Marked.js & Highlight.js with copy-to-clipboard support

---

## 🌟 Key Features

1. **Authentication & User Management:**
   - Sign Up, Login / Sign In, and Logout / Sign Out with secure Django password hashing and validation.
   - User-specific accounts, private data protection, and study metrics persistence.

2. **Student Dashboard:**
   - Personalized greeting with user's name.
   - Study streak tracker (daily active streak in days).
   - Metrics cards: Total study sessions, completed quizzes, average quiz score percentage, and saved topics.
   - Quick action shortcuts to launch chats, explore topics, practice interviews, and take quizzes.
   - Chronological recent activity timeline.

3. **AI Topic Explainer:**
   - Generates structured study content for any topic: High-level summary, detailed conceptual explanation, real-world examples, syntax-highlighted code snippets, and interview tips.
   - Allows students to save explanations to their study profile.
   - One-click shortcut to discuss the topic in AI Chat.

4. **Technical Interview Preparation:**
   - Generates technical interview questions, comprehensive model answers, key talking points, and preparation tips based on subject, target role, and difficulty.
   - Interactive accordion view with collapsible answers and follow-up questions.

5. **MCQ Quiz Generator:**
   - Generates 3–10 multiple-choice questions with 4 distinct options (A, B, C, D) and educational explanations.
   - Interactive test-taking interface with automatic instant scoring and percentage calculation.
   - Visual feedback: highlights correct answers in green, incorrect answers in red, and reveals detailed solutions.
   - Tracks quiz history in database.

6. **AI Study Chat:**
   - Contextual multi-turn follow-up conversations powered by Groq's low-latency inference.
   - Persistent chat history in sidebar, conversation renaming, deleting, and new chat creation.
   - Clear chat feature to reset messages while preserving session.
   - Response regeneration without duplicate user prompts.
   - Interactive code block copying and message copying.
   - Smooth animated loading indicators.

7. **File Upload & Document Analysis:**
   - Upload button inside AI Chat supporting PDF, DOCX, TXT, JPG, JPEG, and PNG files.
   - Automatic text extraction from documents and OCR for images/scanned notes.
   - Content fed directly to Groq AI context window for factual question answering.
   - One-click document actions: Summarize document, generate key study questions & answers, and create MCQ quizzes from uploaded files.
   - File validation, word count badge, and removal button.

8. **Learning History:**
   - Unified learning records hub: view, search, reopen, and delete chats, saved topic explanations, interview prep sessions, and quiz results.
   - Filter tabs for All, Chats, Explanations, Interviews, and Quizzes.

---

## 🚀 Quick Start (Windows)

### 1. Install Dependencies
Open PowerShell or Command Prompt in the project folder and run:
```powershell
pip install -r requirements.txt
```

### 2. Configure Groq API Key
Open `.env` in the project root directory and ensure your Groq API key is present:
```env
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
GROQ_MODEL=qwen/qwen3.8-27b
DEBUG=True
ALLOWED_HOSTS=*
```
*(Get a free API key at [https://console.groq.com/keys](https://console.groq.com/keys)).*

### 3. Apply Database Migrations
```powershell
python manage.py makemigrations chatbot
python manage.py migrate
```

### 4. Run Unit and Integration Tests
```powershell
python manage.py test
```

### 5. Launch Application
```powershell
python manage.py runserver 127.0.0.1:8000
```
Open your browser and navigate to:
**[http://127.0.0.1:8000](http://127.0.0.1:8000)**
