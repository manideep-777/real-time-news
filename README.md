# 📰 Daily Governance News Reporting System

A full-stack application that fetches real-time news articles from Andhra Pradesh using NewsData.io API, summarizes them into categories using Gemini AI, and generates a downloadable daily governance PDF report. The frontend is built in React, and the backend uses Flask, Playwright, and pdfkit.

---

## 🧩 Project Structure

```
project-root/
│
├── backend/
│   ├── app.py
│   ├── templates/
│   │   └── code.html
│   ├── reports/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   └── NewsFileViewer.jsx
│   ├── public/
│   ├── package.json
│   └── ...
│
└── README.md
```

---

## 🚀 Features

- ✅ Fetches Andhra Pradesh news using NewsData.io
- ✅ Cleans and stores news in a structured `.txt` format
- ✅ Categorizes and summarizes news using **Gemini AI**
- ✅ Generates beautiful downloadable **PDF reports** using Playwright
- ✅ Displays articles in React with live fetch + download button

---

## ⚙️ Backend Setup (Flask + Playwright)

1. **Navigate to the backend directory:**

   ```bash
   cd daily_news
   ```
2. **Create a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   ```
3. **Activate the virtual environment:**
   - **On Windows:**
     ```bash
     venv2\Scripts\activate
     ```
   - **On macOS and Linux:**
     ```bash
     source venv/bin/activate
     ```
4. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

5. **Install Playwright and its browsers:**

   ```bash
   <!-- playwright install -->
   python -m playwright install chromium

   ```

6. **Run the Flask server:**

   ```bash
   python main.py
   ```

---

## 🌐 Frontend Setup (React)

1. **Navigate to the frontend directory:**

   ```bash
   cd frontend
   ```

2. **Install dependencies:**

   ```bash
   npm install
   ```

3. **Start the development server:**

   ```bash
   npm run dev
   ```

4. Open your browser at `http://localhost:5173` (or wherever your Vite dev server runs).

---

## 🧠 Gemini AI Key Configuration

In `app.py`, ensure your **Gemini API key** is configured:

```python
google.generativeai.configure(api_key="YOUR_GEMINI_API_KEY")
```

> ⚠️ Keep this key secure and do not expose it publicly.

---

## 📄 Generate the Report

Once the backend and frontend are running:

1. Click **"Fetch Latest News"** → Loads news articles from NewsData.io.
2. Click **"Download PDF"** → Triggers `/generate-pdf` endpoint, which:
   - Summarizes articles using Gemini.
   - Renders summary into HTML.
   - Converts HTML to PDF using Playwright.
   - Downloads the report.

---

## 📦 Sample `requirements.txt`

```txt
Flask
requests
pdfkit
google-generativeai
playwright
flask-cors
```

---

## 🛠 Troubleshooting

- **Playwright not found?** Run `playwright install` inside your Python environment.
- **PDF not generating?** Ensure Chromium is installed (`playwright install` again).
- **CORS errors?** Make sure both frontend and backend are running locally and `flask_cors.CORS(app)` is enabled.

---
