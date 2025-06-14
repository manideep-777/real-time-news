from flask import Flask, jsonify, send_file, render_template
import requests
import re
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright
import os
from flask_cors import CORS
import pdfkit
import google.generativeai


app = Flask(__name__)
CORS(app)

API_KEY = "pub_00262016030b4661a30248582b4b7a00"
NEWS_FILE = "news_data.txt"
MAX_CONTENT_LENGTH = 1000  # max chars in PDF

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"[\u200b\u200c\u200d\uFEFF]", "", text)
    text = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", text)
    text = re.sub(r"\.{3,}", "...", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def severity(article_content):
    # Always return "Low" severity, no AI call
    return "Low"

@app.route("/fetch-news")
def fetch_news():
    url = f"https://newsdata.io/api/1/news?apikey={API_KEY}&country=in&q=Andhra%20Pradesh&size=10"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        articles = data.get("results", [])

        with open(NEWS_FILE, "a", encoding="utf-8") as f:
            for art in articles:
                content_raw = art.get("full_content") or art.get("description") or ""
                content = clean_text(content_raw)
                truncated_content = content[:MAX_CONTENT_LENGTH]

                sev = severity(truncated_content)
                category = "Andhra Pradesh"
                headline = clean_text(art.get("title", "No title"))
                source = clean_text(art.get("source_id", "Unknown"))
                url = clean_text(art.get("link", "No URL"))
                pub_date = clean_text(art.get("pubDate", "Unknown"))

                f.write(f"News Category: {category}\n")
                f.write(f"Headline: {headline}\n")
                f.write(f"Source: {source}\n")
                f.write(f"URL: {url}\n")
                f.write(f"Published Date: {pub_date}\n")    
                f.write(f"Severity: {sev}\n")
                f.write(f"Content:\n{content}\n")
                f.write("-" * 100 + "\n")

        with open(NEWS_FILE, "r", encoding="utf-8") as f:
            file_content = f.read()

        return jsonify({
            "status": "success",
            "articles_fetched": len(articles),
            "news_file_content": file_content
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# old version with fpdf
# @app.route("/generate-pdf")
# def generate_pdf():
#     # Call summarize-news internally
#     summary_response = app.test_client().get("/summarize-news")
#     if summary_response.status_code != 200:
#         return jsonify({"status": "error", "message": "Failed to summarize news"}), 500

#     summary_json = summary_response.get_json()
#     if summary_json["status"] != "success":
#         return jsonify({"status": "error", "message": "Summarize news failed"}), 500

#     categories = summary_json["summary"]["categories"]

#     pdf = PDF()
#     # Load your font
#     pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)

#     pdf.add_page()
#     pdf.set_font("DejaVu", "", 12)  # set regular font

#     # Use only regular font in add_summary
#     pdf.set_font("DejaVu", "", 14)
#     for cat in categories:
#         pdf.cell(0, 10, cat["category_name"], ln=1)
#         pdf.set_font("DejaVu", "", 12)
#         pdf.multi_cell(0, 8, cat["summarized_content"])
#         pdf.ln(5)
#         pdf.set_font("DejaVu", "", 14)  # No bold, just larger size for headings

#     filename = f"daily_governance_report_{datetime.now().strftime('%Y-%m-%d')}.pdf"
#     pdf.output(filename)

#     return send_file(filename, as_attachment=True)

@app.route("/generate-pdf")
def generate_pdf():
    # Get summary JSON
    summary_response = app.test_client().get("/summarize-news")
    if summary_response.status_code != 200:
        return jsonify({"status": "error", "message": "Failed to summarize news"}), 500
    summary_json = summary_response.get_json()
    if summary_json["status"] != "success":
        return jsonify({"status": "error", "message": "Summarize-news failed"}), 500

    categories = summary_json["summary"]["categories"]
    date_str   = datetime.now().strftime("%d-%m-%Y")

    # Render HTML into a temp file
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    html_path   = reports_dir / "daily_report.html"
    html_path.write_text(
        render_template("code.html", date=date_str, categories=categories),
        encoding="utf-8"
    )

    # Launch Playwright to convert HTML → PDF
    pdf_path = reports_dir / f"daily_governance_report_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page    = browser.new_page()
        page.goto(html_path.resolve().as_uri())
        page.emulate_media(media="screen")
        page.pdf(
            path=str(pdf_path),
            format="A4",
            landscape=False,
            # margin={"top": "2cm", "bottom": "2cm", "left": "1.5cm", "right": "1.5cm"}
        )
        browser.close()

    # Send back the generated PDF
    return send_file(str(pdf_path), as_attachment=True)

@app.route("/summarize-news")
def summarize_news():
    if not os.path.exists(NEWS_FILE):
        return jsonify({"status": "error", "message": "No news data available"}), 404

    with open(NEWS_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        return jsonify({"status": "error", "message": "News data file is empty"}), 400

    try:
        # Set up Gemini
        google.generativeai.configure(api_key="AIzaSyDo8O5DdPtYmFeP-Ke7cFnwjlO5W5og124")
        model = google.generativeai.GenerativeModel("models/gemini-1.5-flash-latest")

        # Prompt for 8 categories
        prompt = f"""
You are a top-tier news summarization AI with a focus on regional policy and social impact.

Here is a collection of various news articles:

\"\"\"{content}\"\"\"

Your task:
1. Filter out content that is **not related to Andhra Pradesh**.
2. From the filtered content, extract and summarize only **major issues**, such as:
   - Governance failures
   - Protests, corruption, or political unrest
   - Infrastructure, education, health system concerns
   - Crime, natural disasters, or any major public impact

Output a **JSON object with up to 8 categories**, depending on what is found.

Each category must include:
- category_name (e.g., "Healthcare", "Corruption", "Infrastructure")
- summarized_content (max 3 sentences, focused only on the core issue)

Important:
- Do NOT include general news, entertainment, sports, or non-issue headlines.
- Only include Andhra Pradesh-specific issues.
- Output **only** the pure JSON object with the structure below.

Example:
{{
    "categories": [
        {{
            "category_name": "Law & Order",
            "summarized_content": "A series of violent protests erupted in Vizag over the delay in special status allocation."
        }},
        ...
    ]
}}
"""


        response = model.generate_content(prompt)

        # Optional: clean Gemini output in case it adds extra text
        import json, re
        json_text = re.search(r"\{.*\}", response.text, re.DOTALL)
        if not json_text:
            return jsonify({"status": "error", "message": "Gemini did not return valid JSON"}), 500

        categories_data = json.loads(json_text.group(0))

        return jsonify({
            "status": "success",
            "summary": categories_data
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route("/list-models")
def list_models():
    try:
        google.generativeai.configure(api_key="AIzaSyDo8O5DdPtYmFeP-Ke7cFnwjlO5W5og124")
        models = google.generativeai.list_models()
        models_list = []
        for model in models:
            models_list.append({
                "name": model.name,
                "methods": model.supported_generation_methods
            })
        return jsonify({"models": models_list})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/")
def start_root():
    # Call the summarize-news endpoint internally
    summary_response = app.test_client().get("/summarize-news")
    
    if summary_response.status_code != 200:
        return "Error: Failed to get summary", 500
    
    summary_json = summary_response.get_json()
    
    if summary_json["status"] != "success":
        return "Error: Summarize-news failed", 500
    
    categories = summary_json["summary"]["categories"]
    date_str = datetime.now().strftime("%d-%m-%Y")
    
    return render_template("code.html", date=date_str, categories=categories)


if __name__ == "__main__":
    app.run(debug=True)
