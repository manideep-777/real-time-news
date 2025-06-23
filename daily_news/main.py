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
from googletrans import Translator
from langdetect import detect
import json
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import time
from io import BytesIO
from flask_bcrypt import Bcrypt
import jwt
from dotenv import load_dotenv

if os.getenv("FLASK_ENV") != "production":
    load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)
translator = Translator()

API_KEY = os.getenv("NEWS_API_KEY")
MAX_CONTENT_LENGTH = 1000  

bcrypt = Bcrypt(app)
SECRET_KEY = os.getenv("SECRET_KEY")  

# Connect to MongoDB Atlas
client = MongoClient(os.getenv("MONGO_URI"))

db = client["news_db"]
collection = db["andhra_pradesh_news"]
users_collection = db["users"]

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


def build_issue_check_prompt(article):
    prompt = f"""
You are a governance and public policy AI expert.

Given the following news article details from Andhra Pradesh:

Title: {article.get('title')}
Description: {article.get('description')}
Content: {article.get('content')}
Keywords: {(article.get('keywords', []))}
Categories: {(article.get('category', []))}

Question:
Is this article describing a major public issue, governance problem, social unrest, corruption, crime, or other problem of public interest in Andhra Pradesh? Answer only YES or NO with a short reason if YES.
"""
    return prompt


def check_if_issue(article):
    prompt = build_issue_check_prompt(article)

    # google.generativeai.configure(api_key="AIzaSyDo8O5DdPtYmFeP-Ke7cFnwjlO5W5og124")
    google.generativeai.configure(api_key=os.getenv("GEMINI_KEY"))
    model = google.generativeai.GenerativeModel("models/gemini-1.5-flash-latest")
    
    response = model.generate_content(prompt)
    time.sleep(4)

    answer = response.text.strip()

    # Check if starts with YES, and extract reason if any
    if answer.upper().startswith("YES"):
        # Extract reason after YES, if present
        reason = answer[3:].strip()  # removes 'YES' + spaces
        return True, reason or "No reason provided"
    return False, ""


def safe_translate(text):
    try:
        return translator.translate(text, src='auto', dest='en').text
    except Exception as e:
        print(f"[Translation Error] {e}")
        return text

@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    full_name = data.get("fullName")

    if users_collection.find_one({"email": email}):
        return jsonify({"status": "error", "message": "Email already registered"}), 400

    hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
    user_data = {
        "email": email,
        "password": hashed_pw,
        "full_name": full_name,
        "created_at": datetime.utcnow()
    }
    users_collection.insert_one(user_data)

    payload = {
        "email": email,
        "exp": datetime.utcnow() + timedelta(days=1)
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return jsonify({"status": "success", "message": "User registered", "token": token})


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = users_collection.find_one({"email": email})
    if not user or not bcrypt.check_password_hash(user["password"], password):
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401

    payload = {
        "email": user["email"],
        "exp": datetime.utcnow() + timedelta(days=1)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

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

@app.route("/published-articles-by-date")
def published_articles_by_date():
    date_str = request.args.get("date")  # expects format: YYYY-MM-DD
    if not date_str:
        return jsonify({"status": "error", "message": "Missing 'date' query param"}), 400

    try:
        # Parse and construct full-day UTC range
        time_format = "%Y-%m-%d %H:%M:%S"
        date_start = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        date_end = date_start + timedelta(days=1)

        lower_bound = date_start.strftime(time_format)
        upper_bound = date_end.strftime(time_format)

        query = {
            "published_date": {
                "$gte": lower_bound,
                "$lte": upper_bound
            }
        }

        articles = list(collection.find(query).sort("published_date", -1))
        return jsonify({
            "status": "success",
            "count": len(articles),
            "articles": [
                {
                    "headline": a.get("headline"),
                    "description": a.get("description"),
                    "content": a.get("content"),
                    "published_date": a.get("published_date"),
                    "url": a.get("url"),
                    "issue_reason": a.get("issue_reason"),
                } for a in articles
            ]
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/generate-pdf-by-date")
def generate_pdf_by_date():
    date_str = request.args.get("date")  # expects format: YYYY-MM-DD
    if not date_str:
        return jsonify({"status": "error", "message": "Missing 'date' parameter"}), 400

    # Step 1: Fetch summarized data for specific date
    summary_response = app.test_client().get(f"/summarize-news-by-date?date={date_str}")
    if summary_response.status_code != 200:
        return jsonify({"status": "error", "message": "Failed to summarize news"}), 500

    summary_json = summary_response.get_json()
    if summary_json.get("status") != "success" or not summary_json.get("summary"):
        return jsonify({"status": "error", "message": "Summarization returned no valid data"}), 500

    categories = summary_json["summary"].get("categories", [])
    if not categories or len(categories) < 8:
        return jsonify({"status": "error", "message": "Insufficient categories returned"}), 500

    # Step 2: Render HTML
    formatted_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d-%m-%Y")
    rendered_html = render_template("code.html", date=formatted_date, categories=categories)

    # Step 3: Generate PDF in-memory
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

@app.route("/summarize-news-by-date")
def summarize_news_by_date():
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"status": "error", "message": "Missing 'date' parameter"}), 400

    recent_response = app.test_client().get(f"/published-articles-by-date?date={date_str}")
    if recent_response.status_code != 200:
        return jsonify({"status": "error", "message": "Failed to fetch articles"}), 500

    recent_json = recent_response.get_json()
    if recent_json["status"] != "success" or not recent_json.get("articles"):
        return jsonify({"status": "error", "message": "No valid articles found"}), 404

    articles = recent_json["articles"]
    combined_content = ""
    for art in articles:
        combined_content += f"""
---
Issue: {art.get('issue_reason', '').strip() or 'N/A'}
Headline: {art.get('headline', '').strip()}
Description: {art.get('description', '').strip()}
Content: {art.get('content', '').strip()}
"""

    if not combined_content.strip():
        return jsonify({"status": "error", "message": "No article content to summarize"}), 400

    try:
        google.generativeai.configure(api_key=os.getenv("GEMINI_KEY"))
        model = google.generativeai.GenerativeModel("models/gemini-1.5-flash-latest")

        prompt = f"""
You are a high-precision regional news summarization AI focused on Andhra Pradesh.

Below is a collection of news articles:

\"\"\"{combined_content}\"\"\"

Your task:

1. Analyze the articles and extract **only major public issues** strictly related to **Andhra Pradesh**.
2. Group the issues into **exactly these 8 mandatory categories** (must appear even if few issues exist):
   - Governance
   - Law & Order
   - Healthcare
   - Infrastructure
   - Education
   - Environment
   - Corruption & Politics
   - Agriculture

3. For each of the above 8 categories:
   - Provide **a minimum of 4 real, distinct issues** extracted directly from the articles.
   - If more major issues are found for a category, include them too.
   - Each issue should be **summarized in 1–2 factual sentences**.
   - **Every issue must mention the exact location** (district/city/town).

4. Optionally, if there are **extra categories representing highly critical issues not covered in the 8 above**, include them **after** the 8 categories.

Output Format:
{{
  "categories": [
    {{
      "category_name": "Agriculture",
      "issues": [
        "Example issue in XYZ District...",
        ...
      ]
    }},
    ...
  ]
}}
"""

        response = model.generate_content(prompt)
        json_text = re.search(r"\{.*\}", response.text, re.DOTALL)
        if not json_text:
            return jsonify({"status": "error", "message": "Gemini did not return valid JSON"}), 500

        categories_data = json.loads(json_text.group(0))
        return jsonify({"status": "success", "summary": categories_data})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def get_articles_past_24h_by_published_date():
    now_utc = datetime.now(timezone.utc)
    past_24h_utc = now_utc - timedelta(hours=24)

    # Format expected: "2025-06-20 13:54:43"
    # MongoDB query assumes `published_date` is stored as a string in this format.
    # We convert the time window into string form for comparison.
    time_format = "%Y-%m-%d %H:%M:%S"
    lower_bound = past_24h_utc.strftime(time_format)
    upper_bound = now_utc.strftime(time_format)

    # Query articles where published_date is between lower and upper bounds
    query = {
        "published_date": {
            "$gte": lower_bound,
            "$lte": upper_bound
        }
    }

    cursor = collection.find(query).sort("published_date", -1)  # latest first
    return list(cursor)

@app.route("/recent-published-articles")
def recent_published_articles():
    articles = get_articles_past_24h_by_published_date()
    return jsonify({
        "status": "success",
        "count": len(articles),
        "articles": [
            {
                "headline": a.get("headline"),
                "description": a.get("description"),
                "content": a.get("content"),
                "published_date": a.get("published_date"),
                "url": a.get("url"),
                "issue_reason": a.get("issue_reason"),

            } for a in articles
        ]
    })

@app.route("/fetch-news")
def fetch_news():
    url = f"https://newsdata.io/api/1/news?apikey={API_KEY}&country=in&q=Andhra%20Pradesh&size=50"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        articles = data.get("results", [])

        stored_count = 0

        for art in articles:
            source_priority = art.get("source_priority")
            if source_priority is None or source_priority > 30000:
                continue

            article_id = art.get("article_id")
            if article_id and collection.find_one({ "article_id": article_id }):
                continue

            is_issue, reason = check_if_issue(art)
            if not is_issue:
                continue

            # Clean & fetch fields
            content_raw = art.get("content") or ""
            description_raw = art.get("description") or ""
            headline_raw = art.get("title", "No title")

            # Translate if not in English
            if is_not_english(headline_raw):
                headline_raw = safe_translate(headline_raw)
            if is_not_english(description_raw):
                description_raw = safe_translate(description_raw)
            if is_not_english(content_raw):
                content_raw = safe_translate(content_raw)

            # Final cleaning
            headline = clean_text(headline_raw)
            description = clean_text(description_raw)
            content = clean_text(content_raw)
            truncated_content = content[:MAX_CONTENT_LENGTH]

            source = clean_text(art.get("source_id", "Unknown"))
            url = clean_text(art.get("link", "No URL"))
            pub_date = clean_text(art.get("pubDate", "Unknown"))
            tags = art.get("category", [])
            keywords = art.get("keywords", [])

            # Save to MongoDB
            collection.insert_one({
                "article_id": article_id,
                "headline": headline,
                "source": source,
                "url": url,
                "published_date": pub_date,
                "description": description,
                "content": content,
                "source_priority": source_priority,
                "tags": tags,
                "keywords": keywords,
                "issue_reason": reason,
                "stored_at": datetime.now(timezone.utc)
            })
            stored_count += 1

        return jsonify({
            "status": "success",
            "articles_fetched": stored_count
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/generate-pdf")
def generate_pdf():
    try:
        # Step 1: Fetch summarized data
        summary_response = app.test_client().get("/summarize-news")
        if summary_response.status_code != 200:
            return jsonify({"status": "error", "message": "Failed to summarize news"}), 500

        summary_json = summary_response.get_json()
        if summary_json.get("status") != "success" or not summary_json.get("summary"):
            return jsonify({"status": "error", "message": "Summarization returned no valid data"}), 500

        categories = summary_json["summary"].get("categories", [])
        if not categories or len(categories) < 8:
            return jsonify({"status": "error", "message": "Insufficient categories returned"}), 500

        # Step 2: Render HTML from Jinja2
        date_str = datetime.now().strftime("%d-%m-%Y")
        rendered_html = render_template("code.html", date=date_str, categories=categories)

        # Step 3: Generate PDF in-memory using Playwright
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

        # Step 4: Return as downloadable file
        filename = f"daily_governance_report_{datetime.now().strftime('%Y-%m-%d')}.pdf"
        return send_file(pdf_buffer, mimetype="application/pdf", as_attachment=True, download_name=filename)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/summarize-news")
def summarize_news():
    # Fetch recent published articles from internal API
    recent_response = app.test_client().get("/recent-published-articles")
    if recent_response.status_code != 200:
        return jsonify({"status": "error", "message": "Failed to fetch recent articles"}), 500

    recent_json = recent_response.get_json()
    if recent_json["status"] != "success" or not recent_json.get("articles"):
        return jsonify({"status": "error", "message": "No valid recent articles found"}), 404

    # Extract and combine fields from each article
    articles = recent_json["articles"]
    combined_content = ""

    for art in articles:
        headline = art.get("headline", "").strip()
        description = art.get("description", "").strip()
        content = art.get("content", "").strip()
        issue_reason = art.get("issue_reason", "").strip()

        combined_content += f"""
---
Issue: {issue_reason if issue_reason else "N/A"}
Headline: {headline}
Description: {description}
Content: {content}
"""

    if not combined_content.strip():
        return jsonify({"status": "error", "message": "No article content to summarize"}), 400

    try:
        # Configure Gemini API
        google.generativeai.configure(api_key=os.getenv("GEMINI_KEY"))
        model = google.generativeai.GenerativeModel("models/gemini-1.5-flash-latest")

        # Summarization prompt
        prompt = f"""
You are a high-precision regional news summarization AI focused on Andhra Pradesh.

Below is a collection of news articles:

\"\"\"{combined_content}\"\"\"

Your task:

1. Analyze the articles and extract **only major public issues** strictly related to **Andhra Pradesh**.
2. Group the issues into **exactly these 8 mandatory categories** (must appear even if few issues exist):
   - Governance
   - Law & Order
   - Healthcare
   - Infrastructure
   - Education
   - Environment
   - Corruption & Politics
   - Agriculture

3. For each of the above 8 categories:
   - Provide **a minimum of 4 real, distinct issues** extracted directly from the articles.
   - If more major issues are found for a category, include them too.
   - Each issue should be **summarized in 1–2 factual sentences**.
   - **Every issue must mention the exact location** (district/city/town).

4. Optionally, if there are **extra categories representing highly critical issues not covered in the 8 above**, include them **after** the 8 categories — but only if they are clearly distinct and well-supported.

**Rules**:
- Do NOT fabricate or generalize issues.
- Do NOT include non-issue topics (like entertainment, sports, lifestyle).
- Do NOT omit any of the 8 mandatory categories.
- Output should contain **at least 8 categories**, and more only if necessary.

Output Format (strictly this JSON structure):

{{
  "categories": [
    {{
      "category_name": "Agriculture",
      "issues": [
        "Farmers in Anantapur district reported severe losses due to delayed monsoon and lack of irrigation support.",
        "Paddy fields in West Godavari were submerged after an unexpected canal breach, damaging over 200 acres.",
        "In Guntur, chilli farmers protested over sharp decline in market prices and lack of government procurement.",
        "Kadapa farmers complained about unavailability of subsidized fertilizers during the sowing season."
      ]
    }},
    ...
  ]
}}

Instructions:
- Output only the JSON object — no extra explanations, markdown, or formatting.
- The output must be valid JSON.
"""

        # Generate and parse response
        response = model.generate_content(prompt)
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
        google.generativeai.configure(api_key=os.getenv("GEMINI_KEY"))
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


def fetch_news_job():
    with app.app_context():
        # Use Flask test client to call your /fetch-news endpoint internally
        response = app.test_client().get("/fetch-news")
        print(f"[Fetch @ {datetime.now()}] Status: {response.status_code}")
        try:
            print(response.get_json())
        except Exception:
            print("Invalid JSON response")

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=fetch_news_job, trigger="interval", minutes=5)
    scheduler.start()

    fetch_news_job()

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())
    # app.run(debug=False, use_reloader=False)
    app.run(debug=True, use_reloader=False)
    # app.run(debug=True)
