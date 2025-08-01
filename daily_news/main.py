from flask import Flask, jsonify, send_file, render_template, request
import requests
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright
import os
from flask_cors import CORS
import pdfkit
import google.generativeai
from pymongo import MongoClient
from deep_translator import GoogleTranslator
from langdetect import detect
import json
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import time
from io import BytesIO
from flask_bcrypt import Bcrypt
import jwt
from dotenv import load_dotenv
from difflib import SequenceMatcher

import anthropic

# Load environment variables
# if os.getenv("FLASK_ENV") != "production":
#     load_dotenv()

load_dotenv()

# --- Client Initializations ---
app = Flask(__name__)
CORS(app, supports_credentials=True)
# translator = GoogleTranslator(source='auto', target='en')

# Securely load keys from environment variables
API_KEY = os.getenv("NEWS_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# print("ANTHROPIC_API_KEY:", repr(ANTHROPIC_API_KEY))

# Check for missing environment variables
if not all([API_KEY, SECRET_KEY, ANTHROPIC_API_KEY]):
    raise ValueError("One or more critical environment variables (NEWS_API_KEY, SECRET_KEY, TOGETHER_API_KEY) are missing.")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# --- Constants ---
MAX_CONTENT_LENGTH = 1000

# --- Flask Extensions ---
bcrypt = Bcrypt(app)

# --- Database Connection ---
client2 = MongoClient(os.getenv("MONGO_URI"))
db = client2["news_db"]
collection = db["andhra_pradesh_news"]
users_collection = db["users"]

# --- Helper Functions ---

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"[\u200b\u200c\u200d\uFEFF]", "", text)
    text = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", text)
    text = re.sub(r"\.{3,}", "...", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def is_not_english(text):
    try:
        return detect(text) != "en"
    except:
        return False

# def safe_translate(text, retries=3):
#     for attempt in range(retries):
#         try:
#             return translator.translate(text)
#         except Exception as e:
#             print(f"[Translation Error - attempt {attempt+1}] {e}")
#             time.sleep(1)  # short delay before retry
#     return text  # fallback: return original text if all retries fail

# --- AI & Logic Functions ---



# def build_issue_check_prompt(article):
#     prompt = """
# You are a governance and public policy AI expert.

# You will be given a single news article from Andhra Pradesh or nearby regions.

# Your task:
# - Determine whether the article discusses a major negative issue such as:
#   - Public problems, governance failures, crime, unrest, corruption, disasters, or any serious public concern.
# - ⛔ Strictly EXCLUDE:
#   - Telangana-related news
#   - Any political coverage (election campaigns, party statements, leader speeches, political promotion)
# - ✅ Only include stories impacting the general public negatively and located in Andhra Pradesh.

# Output rules:
# - If the article is NOT an issue or is about Telangana or politics, return ONLY:
#   {"is_issue": "NO"}

# - If it IS a public issue in Andhra Pradesh, return ONLY the following full JSON object:
# {
#   "headline": "<Original headline in English (translate if in Telugu)>",
#   "description": "<Original description in English (translate if in Telugu)>",
#   "headline_ai": "<5–6 word summary>",
#   "is_issue": "YES",
#   "reason_html": "<3-line HTML explanation with <b>Location</b>>",
#   "description_ai": "<2-paragraph English summary>",
#   "content": "<2-paragraph English summary>"
# }

# Instructions:
# - If `headline` or `description` is in Telugu, translate to English and return.
# - If already in English, keep as is.
# - Translate and summarize `description` and `content` into fluent English (2 short paragraphs).
# - NEVER include anything outside the required JSON object.
# """

#     def clean_for_prompt(text):
#         return ''.join(c for c in text if c.isprintable()).strip()

#     title = clean_for_prompt(article.get("title", ""))
#     desc = clean_for_prompt(article.get("description") or "")
#     content = clean_for_prompt(article.get("content") or "")
#     keywords = article.get("keywords") or []

#     prompt += f"""
# Original Headline: {title}
# Description: {desc}
# Content: {content[:1000]}
# Keywords: {keywords}
# """
#     return prompt.strip()


def build_issue_check_prompt(article):
    prompt = """
You are a governance and public policy AI expert.

You will be given a single news article from Andhra Pradesh or nearby regions.

Your task:
1. Determine whether the article discusses a **major negative issue** such as:
   - Public problems, governance failures, crime, unrest, corruption, disasters, or any serious public concern.

2. ⛔ Strictly EXCLUDE:
   - Telangana-related news
   - Any political coverage (election campaigns, party statements, leader speeches, political promotion)

3. ✅ Only include stories impacting the **general public negatively** and **located in Andhra Pradesh**.

---

Your responsibilities:
- Read the article and identify if it's a serious public issue.
- If yes, classify the issue into **one appropriate government department** from the list below.
- Departments are used to route issues to the right authorities.

---

🛑 If the article is NOT a public issue or is about Telangana/politics, return:
```json
{"is_issue": "NO"}
✅ If it is a public issue, return the following structured JSON:
{
  "headline": "<Original headline in English (translate if in Telugu)>",
  "description": "<Original description in English (translate if in Telugu)>",
  "headline_ai": "<5–6 word summary>",
  "is_issue": "YES",
  "reason_html": "<3-line HTML explanation with <b>Location</b>>",
  "description_ai": "<2-paragraph English summary>",
  "content": "<2-paragraph English summary>",
  "department": "<Select the best-fit department from the list below>"
}
Available Departments:
Agriculture And Co-operation, Animal Husbandry, Dairy Development and Fisheries, AP NRTS, APPSC, Backward Classes Welfare, Chief Minister's relief fund (CMRF), Consumer Affairs, Food and Civil Supplies, Corona, Department of Economically Weaker Sections Welfare, Department of Skills Development and Training, Disaster Management, Energy, Environment, Forest, Science And Technology, Finance, General Administration, Grama Volunteers/Ward Volunteers And Village Secretariats/Ward Secretariats, Health, Medical And Family Welfare, Home, Housing, Human Resources (Higher Education), Human Resources (School Education), Industries and Commerce, Information Technology, Electronics and Communications, Infrastructure And Investments, Labour, Factories, Boilers And Insurance Medical Services, Law, Minorities Welfare, Municipal Administration And Urban Development, Panchayat Raj And Rural Development, Planning, Public Enterprises, Revenue, Social Welfare, Transport, Roads and Buildings, Tribal Welfare, Water Resources, Women, Children, Disabled and Senior Citizens, Youth Advancement, Tourism And Culture.
Instructions:
Detect and translate headline or description if in Telugu.
Translate and summarize description and content in fluent English.
Match the core issue with the most related department.

⚠️ Output must be only valid JSON — no markdown, explanation, or formatting outside the JSON.
"""

    def clean_for_prompt(text):
        return ''.join(c for c in text if c.isprintable()).strip()

    title = clean_for_prompt(article.get("title", ""))
    desc = clean_for_prompt(article.get("description") or "")
    content = clean_for_prompt(article.get("content") or "")
    keywords = article.get("keywords") or []

    prompt += f"""

Original Headline: {title}
Description: {desc}
Content: {content[:1000]}
Keywords: {keywords}
"""
    return prompt.strip()


def check_if_issue(article):
    prompt = build_issue_check_prompt(article)
    print("Prompt length:", len(prompt))
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens= 8000, 
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        time.sleep(3)

        if not response or not getattr(response, "content", None):
            print("❌ Claude returned empty content.")
            return None

        raw = response.content[0].text.strip()
        clean_raw = ''.join(c for c in raw if c.isprintable())
        match = re.search(r"\{.*\}", clean_raw, re.DOTALL)
        if not match:
            print("❌ Claude response did not contain valid JSON object.")
            return None

        parsed = json.loads(match.group(0))
        print("Parsed response:", parsed)
        return parsed

    except Exception as e:
        print("❌ Claude API request failed:", e)
        return None



def fetch_and_store_news_logic():
    urls = [
        f"https://newsdata.io/api/1/news?apikey={API_KEY}&country=in&q=Andhra%20Pradesh&size=50&removeduplicate=1&prioritydomain=top",
        f"https://newsdata.io/api/1/news?apikey={API_KEY}&country=in&q=Andhra%20Pradesh&size=50&removeduplicate=1&prioritydomain=medium"
    ]

    stored_count = 0
    seen_ids = set()

    try:
        all_articles = []
        existing_headlines = [
            doc["headline"] for doc in collection.find({}, {"headline": 1}) if doc.get("headline")
        ]
        for url in urls:
            resp = requests.get(url)
            resp.raise_for_status()
            articles = resp.json().get("results", [])
            for art in articles:
                article_id = art.get("article_id")
                if not article_id or article_id in seen_ids:
                    continue
                seen_ids.add(article_id)

                source_priority = art.get("source_priority")
                if source_priority is None or source_priority > 30000:
                    continue

                if collection.find_one({"article_id": article_id}):
                    continue

                if collection.find_one({"headline": art.get("title")}):
                    continue

                if collection.find_one({"url": art.get("link")}):
                    continue

                all_articles.append(art)

        for article in all_articles:
            result = check_if_issue(article)
            if not result or not isinstance(result, dict):
                continue

            if result.get("is_issue") != "YES":
                # time.sleep(3)
                continue

            collection.insert_one({
                "article_id": article.get("article_id"),
                "headline": clean_text(result.get("headline", "No headline")),
                "headline_ai": clean_text(result.get("headline_ai", "No headline")),
                "source": clean_text(article.get("source_id", "Unknown")),
                "url": clean_text(article.get("link", "No URL")),
                "published_date": clean_text(article.get("pubDate", "Unknown")),
                "description": clean_text(result.get("description", "")),
                "description_ai": clean_text(result.get("description_ai", "")),
                "content": clean_text(result.get("content", "")),
                "source_priority": article.get("source_priority"),
                "tags": article.get("category", []),
                "keywords": article.get("keywords", []),
                "issue_reason": result.get("reason_html", ""),
                "stored_at": datetime.now(timezone.utc),
                "department": result.get("department", "Unknown"),
            })
            stored_count += 1
            time.sleep(3)

        return {"status": "success", "articles_fetched": stored_count}

    except Exception as e:
        print(e)
        return {"status": "error", "message": str(e)}


def get_articles_logic(time_format="%Y-%m-%d %H:%M:%S", date_str=None):
    """Fetches articles from the DB, either from the last 24h or for a specific date."""
    if date_str:
        date_start = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        date_end = date_start + timedelta(days=1)
        lower_bound = date_start.strftime(time_format)
        upper_bound = date_end.strftime(time_format)
    else:
        now_utc = datetime.now(timezone.utc)
        past_24h_utc = now_utc - timedelta(hours=24)
        lower_bound = past_24h_utc.strftime(time_format)
        upper_bound = now_utc.strftime(time_format)

    query = {"published_date": {"$gte": lower_bound, "$lte": upper_bound}}
    articles = list(collection.find(query).sort("published_date", -1))
    
    
    return [
        {
            "headline": a.get("headline"),
            "headline_ai": a.get("headline_ai"),
            "description": a.get("description"),
            "content": a.get("content"),
            "published_date": a.get("published_date"),
            "url": a.get("url"),
            "issue_reason": a.get("issue_reason"),
            "department": a.get("department"),
        } for a in articles
    ]

def summarize_news_logic(articles):
    """Contains the logic to summarize a list of articles."""
    if not articles:
        return {"status": "error", "message": "No articles to summarize"}

    combined_content = ""
    for art in articles:
        headline = art.get("headline_ai", "").strip()
        reason = art.get("issue_reason", "N/A").strip()
        combined_content += f"- {headline} (Issue: {reason})\n"

    prompt = f"""
You are a high-precision regional news summarization AI focused on Andhra Pradesh.

Below is a list of public news issues, each with a short explanation:
\"\"\"{combined_content}\"\"\"

Your task:
1. Go through all issues and **ONLY INCLUDE major public issues** — serious concerns such as:
   - Governance failures, disasters, crime, corruption, unrest, major public complaints, severe infrastructure problems, public health crises, or service delivery failures.
2. Ignore and exclude minor updates, political promotion, soft news, or Telangana-related content.
3. Group valid issues into **logical categories** such as Floods, Crime, Accidents, Education, Healthcare, Infrastructure, Corruption, etc.
4. The number and type of categories must be **dynamically decided** based on content.
5. Each issue should stay in its **original sentence form**, with **location** (district/city/town) included.

Respond ONLY in this strict JSON format:
{{
  "categories": [
    {{
      "category_name": "Generated Category",
      "issues": [
        "Issue summary 1 with location...",
        "Issue summary 2 with location...",
        ...
      ]
    }},
    ...
  ]
}}

⚠️ Return **only the JSON**. No explanations, comments or markdown.
"""
    try:
        response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens= 8000, 
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )
        text = response.content[0].text.strip()
        print(text)
        json_text = re.search(r"\{.*\}", text, re.DOTALL)
        if not json_text:
            return {"status": "error", "message": "Model did not return valid JSON"}

        summary = json.loads(json_text.group(0))
        return {"status": "success", "summary": summary}

    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- API Endpoints ---

# @app.route("/signup", methods=["POST"])
# def signup():
#     data = request.json
#     username = data.get("username")
#     password = data.get("password")

#     if users_collection.find_one({"username": username}):
#         return jsonify({"status": "error", "message": "Username already taken"}), 400

#     hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
#     users_collection.insert_one({
#         "username": username,
#         "password": hashed_pw,
#         "created_at": datetime.utcnow()
#     })

#     token = jwt.encode({
#         "username": username,
#         "exp": datetime.utcnow() + timedelta(days=1)
#     }, SECRET_KEY, algorithm="HS256")
#     return jsonify({"status": "success", "message": "User registered", "token": token})


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    user = users_collection.find_one({"username": username})
    if not user or not bcrypt.check_password_hash(user["password"], password):
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401

    token = jwt.encode({
        "username": user["username"],
        "exp": datetime.utcnow() + timedelta(days=1)
    }, SECRET_KEY, algorithm="HS256")
    return jsonify({"status": "success", "token": token})


@app.route("/is-authenticated", methods=["GET"])
def is_authenticated():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"authenticated": False, "message": "Token missing"}), 401
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return jsonify({"authenticated": True, "username": decoded["username"]}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"authenticated": False, "message": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"authenticated": False, "message": "Invalid token"}), 401


@app.route("/fetch-news")
def fetch_news_endpoint():
    result = fetch_and_store_news_logic()
    print(result)
    status_code = 500 if result["status"] == "error" else 200
    return jsonify(result), status_code

@app.route("/recent-published-articles")
def recent_published_articles_endpoint():
    articles = get_articles_logic()
    return jsonify({"status": "success", "count": len(articles), "articles": articles})

@app.route("/published-articles-by-date")
def published_articles_by_date_endpoint():
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"status": "error", "message": "Missing 'date' query param"}), 400
    
    try:
        articles = get_articles_logic(date_str=date_str)
        return jsonify({"status": "success", "count": len(articles), "articles": articles})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/summarize-news")
def summarize_news_endpoint():
    articles = get_articles_logic() # Get last 24h articles
    if not articles:
        return jsonify({"status": "error", "message": "No recent articles found to summarize"}), 404
    
    result = summarize_news_logic(articles)
    status_code = 500 if result["status"] == "error" else 200
    return jsonify(result), status_code

@app.route("/summarize-news-by-date")
def summarize_news_by_date_endpoint():
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"status": "error", "message": "Missing 'date' parameter"}), 400

    articles = get_articles_logic(date_str=date_str)
    if not articles:
        return jsonify({"status": "error", "message": "No articles found for that date"}), 404

    result = summarize_news_logic(articles)
    status_code = 500 if result["status"] == "error" else 200
    return jsonify(result), status_code


@app.route("/generate-pdf")
def generate_pdf_endpoint():
    articles = get_articles_logic() # Get last 24h articles
    if not articles:
        return jsonify({"status": "error", "message": "No recent articles found to generate PDF"}), 404
        
    summary_data = summarize_news_logic(articles)
    if summary_data.get("status") != "success":
        return jsonify(summary_data), 500

    categories = summary_data["summary"].get("categories", [])
    if not categories:
        return jsonify({"status": "error", "message": "No categories returned for PDF"}), 500

    try:
        date_str = datetime.now().strftime("%d-%m-%Y")
        rendered_html = render_template("code.html", date=date_str, categories=categories)
        
        pdf_buffer = BytesIO()
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(rendered_html)
            page.emulate_media(media="screen")
            pdf_bytes = page.pdf(format="A4", landscape=False)
            browser.close()
            pdf_buffer.write(pdf_bytes)
            pdf_buffer.seek(0)

        filename = f"daily_governance_report_{datetime.now().strftime('%Y-%m-%d')}.pdf"
        return send_file(pdf_buffer, mimetype="application/octet-stream", as_attachment=True, download_name=filename)
    except Exception as e:
        print(e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/generate-pdf-by-date")
def generate_pdf_by_date_endpoint():
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"status": "error", "message": "Missing 'date' parameter"}), 400

    articles = get_articles_logic(date_str=date_str)
    if not articles:
        return jsonify({"status": "error", "message": f"No articles found for date {date_str}"}), 404

    summary_data = summarize_news_logic(articles)
    if summary_data.get("status") != "success":
        return jsonify(summary_data), 500

    categories = summary_data["summary"].get("categories", [])
    if not categories:
        return jsonify({"status": "error", "message": "No categories returned for PDF"}), 500

    try:
        formatted_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d-%m-%Y")
        rendered_html = render_template("code.html", date=formatted_date, categories=categories)

        pdf_buffer = BytesIO()
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(rendered_html)
            page.emulate_media(media="screen")
            pdf_bytes = page.pdf(format="A4", landscape=False)
            browser.close()
            pdf_buffer.write(pdf_bytes)
            pdf_buffer.seek(0)

        filename = f"daily_governance_report_{date_str}.pdf"
        return send_file(pdf_buffer, mimetype="application/pdf", as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/")
def start_root():
    articles = get_articles_logic()
    if not articles:
        return "Error: No recent articles found to display.", 500
        
    summary_data = summarize_news_logic(articles)
    if summary_data.get("status") != "success":
        return f"Error: Failed to get summary - {summary_data.get('message')}", 500
    
    categories = summary_data["summary"]["categories"]
    date_str = datetime.now().strftime("%d-%m-%Y")
    
    return render_template("code.html", date=date_str, categories=categories)


@app.route("/search-articles", methods=["GET"])
def search_articles():
    keyword = request.args.get("keyword")
    if not keyword:
        return jsonify({"status": "error", "message": "Missing 'keyword' parameter"}), 400

    keyword = keyword.lower()

    # Build regex query (case-insensitive)
    regex = {"$regex": re.escape(keyword), "$options": "i"}

    query = {
        "$or": [
            {"headline": regex},
            {"headline_ai": regex},
            {"description": regex},
            {"description_ai": regex},
            {"content": regex},
            {"tags": regex},
            {"keywords": regex},
            {"issue_reason": regex},
        ]
    }

    try:
        results = list(collection.find(query).sort("published_date", -1))
        articles = [
            {
                "headline": a.get("headline"),
                "headline_ai": a.get("headline_ai"),
                "description": a.get("description"),
                "description_ai": a.get("description_ai"),
                "content": a.get("content"),
                "tags": a.get("tags"),
                "keywords": a.get("keywords"),
                "published_date": a.get("published_date"),
                "url": a.get("url"),
                "issue_reason": a.get("issue_reason"),
                "department": a.get("department"),
            }
            for a in results
        ]
        return jsonify({"status": "success", "count": len(articles), "articles": articles})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



# --- Background Scheduler ---

def fetch_news_job():
    """Scheduled job to fetch news."""
    with app.app_context():
        print(f"[Scheduler @ {datetime.now()}] Running fetch_and_store_news_logic...")
        result = fetch_and_store_news_logic()
        print(f"[Scheduler @ {datetime.now()}] Result: {result}")


if __name__ == "__main__":
# Initialize and start the scheduler
    scheduler = BackgroundScheduler()
    # scheduler.add_job(func=fetch_news_job, trigger="interval", minutes=10)
    scheduler.add_job(fetch_news_job, trigger="cron", hour=6, minute=0)
    scheduler.start()

    # # Initial run on startup
    with app.app_context():
        fetch_news_job()

    # # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())
    app.run(debug=False, use_reloader=False)
    # app.run(debug=True)

# To run this application in a production environment using IIS (Internet Information Services),
# you will need to use a WSGI gateway like wfastcgi.
#
# 1. Ensure IIS has the CGI module enabled.
# 2. Install wfastcgi: pip install wfastcgi
# 3. Configure IIS to use your Python installation by running: wfastcgi-enable
# 4. Create a web.config file in this directory to point IIS to your Flask app.
#
# You will also need to set the following environment variables in your IIS application settings:
# - FLASK_ENV=production
# - NEWS_API_KEY
# - SECRET_KEY
# - TOGETHER_API_KEY
# - MONGO_URI