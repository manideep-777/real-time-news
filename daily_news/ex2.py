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

from together import Together

# Load environment variables
if os.getenv("FLASK_ENV") != "production":
    load_dotenv()

# --- Client Initializations ---
app = Flask(__name__)
CORS(app, supports_credentials=True)
translator = GoogleTranslator(source='auto', target='en')

# Securely load keys from environment variables
API_KEY = os.getenv("NEWS_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

# Check for missing environment variables
if not all([API_KEY, SECRET_KEY, TOGETHER_API_KEY]):
    raise ValueError("One or more critical environment variables (NEWS_API_KEY, SECRET_KEY, TOGETHER_API_KEY) are missing.")

client_together = Together(api_key=TOGETHER_API_KEY)

# --- Constants ---
MAX_CONTENT_LENGTH = 1000

# --- Flask Extensions ---
bcrypt = Bcrypt(app)

# --- Database Connection ---
client = MongoClient(os.getenv("MONGO_URI"))
db = client["news_db"]
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

def safe_translate(text):
    try:
        return translator.translate(text)
    except Exception as e:
        print(f"[Translation Error] {e}")
        return text

# --- AI & Logic Functions ---

def build_issue_check_prompt(article):
    content = article.get('content') or ""
    content_truncated = content[:1000]
    return f"""
You are a governance and public policy AI expert.

Given the following news article details from Andhra Pradesh:

Title: {article.get('title')}
Description: {article.get('description')}
Content: {content_truncated}
Keywords: {article.get('keywords', [])}
Categories: {article.get('category', [])}

Question:
Is this article describing a major public issue, governance problem, social unrest, corruption, crime, or other problem of public interest in Andhra Pradesh? Answer only YES or NO with a short reason if YES.
"""

def check_if_issue(article):
    prompt = build_issue_check_prompt(article)
    try:
        response = client_together.chat.completions.create(
            model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
            temperature=0.2
        )
        time.sleep(2)
        answer = response.choices[0].message.content.strip()

        if answer.upper().startswith("YES"):
            reason = answer[3:].strip()
            return True, reason or "No reason provided"
        return False, ""
    except Exception as e:
        print("Issue check failed:", str(e))
        return False, ""

@app.route("/top")
def top():
    priority = []

    # Fetch top 10% domains
    url_top = f"https://newsdata.io/api/1/news?apikey={API_KEY}&country=in&q=Andhra%20Pradesh&size=50&removeduplicate=1&prioritydomain=top"
    resp_top = requests.get(url_top)
    resp_top.raise_for_status()
    articles_top = resp_top.json().get("results", [])

    # Fetch top 30% (medium, includes top again — we'll deduplicate)
    url_medium = f"https://newsdata.io/api/1/news?apikey={API_KEY}&country=in&q=Andhra%20Pradesh&size=50&removeduplicate=1&prioritydomain=medium"
    resp_medium = requests.get(url_medium)
    resp_medium.raise_for_status()
    articles_medium = resp_medium.json().get("results", [])

    # Combine and deduplicate based on article_id
    seen_ids = set()
    combined = articles_top + articles_medium
    for art in combined:
        if (aid := art.get("article_id")) and aid not in seen_ids:
            seen_ids.add(aid)
            source_priority = art.get("source_priority")
            priority.append(source_priority)

    return priority
    
def fetch_and_store_news_logic():
    """Contains the logic to fetch, process, and store news articles."""
    url = f"https://newsdata.io/api/1/news?apikey={API_KEY}&country=in&q=Andhra%20Pradesh&size=50&removeduplicate=1"
    stored_count = 0
    
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        articles = data.get("results", [])
        

        for art in articles:
            source_priority = art.get("source_priority")
            if source_priority is None or source_priority > 30000:
                continue

            article_id = art.get("article_id")
            if article_id and collection.find_one({"article_id": article_id}):
                continue

            is_issue, reason = check_if_issue(art)
            if not is_issue:
                time.sleep(15)
                continue

            content_raw = art.get("content") or ""
            description_raw = art.get("description") or ""
            headline_raw = art.get("title", "No title")

            if is_not_english(headline_raw):
                headline_raw = safe_translate(headline_raw)
            if is_not_english(description_raw):
                description_raw = safe_translate(description_raw)
            if is_not_english(content_raw):
                content_raw = safe_translate(content_raw)

            collection.insert_one({
                "article_id": article_id,
                "headline": clean_text(headline_raw),
                "source": clean_text(art.get("source_id", "Unknown")),
                "url": clean_text(art.get("link", "No URL")),
                "published_date": clean_text(art.get("pubDate", "Unknown")),
                "description": clean_text(description_raw),
                "content": clean_text(content_raw),
                "source_priority": source_priority,
                "tags": art.get("category", []),
                "keywords": art.get("keywords", []),
                "issue_reason": reason,
                "stored_at": datetime.now(timezone.utc)
            })
            stored_count += 1
        
        return {"status": "success", "articles_fetched": stored_count}

    except Exception as e:
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
            "description": a.get("description"),
            "content": a.get("content"),
            "published_date": a.get("published_date"),
            "url": a.get("url"),
            "issue_reason": a.get("issue_reason"),
        } for a in articles
    ]

def summarize_news_logic(articles):
    """Contains the logic to summarize a list of articles."""
    if not articles:
        return {"status": "error", "message": "No articles to summarize"}

    combined_content = ""
    for art in articles:
        headline = art.get("headline", "").strip()
        reason = art.get("issue_reason", "N/A").strip()
        combined_content += f"- {headline} (Issue: {reason})\n"

    prompt = f"""
You are a high-precision regional news summarization AI focused on Andhra Pradesh.
Below is a list of headlines and their issue reasons:
\"\"\"{combined_content}\"\"\"
Your task:
1. Extract only **major public issues** strictly related to Andhra Pradesh.
2. Group them into **exactly 8 mandatory categories**:
   - Governance, Law & Order, Healthcare, Infrastructure, Education, Environment, Corruption & Politics, Agriculture
3. For each category:
   - Provide **at least 4 real issues**.
   - Each issue should be **1–2 sentences** and include **exact location** (district/city/town).
Output JSON format (strict):
{{
  "categories": [
    {{ "category_name": "Agriculture", "issues": ["Example issue in XYZ District..."] }},
    ...
  ]
}}
Only return the JSON. No extra formatting or explanation.
"""
    try:
        response = client_together.chat.completions.create(
            model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
            messages=[
                {"role": "system", "content": "You are a factual news summarizer."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2048,
            temperature=0.3,
        )
        text = response.choices[0].message.content
        json_text = re.search(r"\{.*\}", text, re.DOTALL)
        if not json_text:
            return {"status": "error", "message": "Model did not return valid JSON"}

        summary = json.loads(json_text.group(0))
        return {"status": "success", "summary": summary}

    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- API Endpoints ---

@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    full_name = data.get("fullName")

    if users_collection.find_one({"email": email}):
        return jsonify({"status": "error", "message": "Email already registered"}), 400

    hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
    users_collection.insert_one({
        "email": email,
        "password": hashed_pw,
        "full_name": full_name,
        "created_at": datetime.utcnow()
    })

    token = jwt.encode({
        "email": email,
        "exp": datetime.utcnow() + timedelta(days=1)
    }, SECRET_KEY, algorithm="HS256")
    return jsonify({"status": "success", "message": "User registered", "token": token})

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = users_collection.find_one({"email": email})
    if not user or not bcrypt.check_password_hash(user["password"], password):
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401

    token = jwt.encode({
        "email": user["email"],
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
        return jsonify({"authenticated": True, "email": decoded["email"]}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"authenticated": False, "message": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"authenticated": False, "message": "Invalid token"}), 401

@app.route("/fetch-news")
def fetch_news_endpoint():
    result = fetch_and_store_news_logic()
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

@app.route("/api/articles")
def api_articles():
    """Retrieves all articles from the database and saves them to a JSON file."""
    try:
        articles_cursor = collection.find().sort("stored_at", -1)
        articles_list = []
        for article in articles_cursor:
            article["_id"] = str(article["_id"])
            article.pop("issue_reason", None)  # Remove 'issue_reason' field if present
            
            if "published_date" in article and isinstance(article["published_date"], datetime):
                article["published_date"] = article["published_date"].isoformat()
            if "stored_at" in article and isinstance(article["stored_at"], datetime):
                article["stored_at"] = article["stored_at"].isoformat()
            
            articles_list.append(article)

        # Define the path for the new JSON file
        reports_dir = Path(__file__).parent / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"all_articles_{timestamp}.json"
        file_path = reports_dir / file_name

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({"count": len(articles_list), "articles": articles_list}, f, ensure_ascii=False, indent=4)

        return jsonify({"status": "success", "message": f"All articles saved to {file_path}"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/generate-pdf")
def generate_pdf_endpoint():
    articles = get_articles_logic() # Get last 24h articles
    if not articles:
        return jsonify({"status": "error", "message": "No recent articles found to generate PDF"}), 404
        
    summary_data = summarize_news_logic(articles)
    if summary_data.get("status") != "success":
        return jsonify(summary_data), 500

    categories = summary_data["summary"].get("categories", [])
    if not categories or len(categories) < 8:
        return jsonify({"status": "error", "message": "Insufficient categories returned for PDF"}), 500

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
        return send_file(pdf_buffer, mimetype="application/pdf", as_attachment=True, download_name=filename)
    except Exception as e:
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
    if not categories or len(categories) < 8:
        return jsonify({"status": "error", "message": "Insufficient categories returned for PDF"}), 500

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

# --- Background Scheduler ---

def fetch_news_job():
    """Scheduled job to fetch news."""
    with app.app_context():
        print(f"[Scheduler @ {datetime.now()}] Running fetch_and_store_news_logic...")
        result = fetch_and_store_news_logic()
        print(f"[Scheduler @ {datetime.now()}] Result: {result}")


if __name__ == "__main__":
# Initialize and start the scheduler
    # scheduler = BackgroundScheduler()
    # scheduler.add_job(func=fetch_news_job, trigger="interval", minutes=10)
    # scheduler.start()

    # # Initial run on startup
    # with app.app_context():
    #     fetch_news_job()

    # # Shut down the scheduler when exiting the app
    # atexit.register(lambda: scheduler.shutdown())
    # app.run(debug=False, use_reloader=False)
    app.run(debug=True)

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