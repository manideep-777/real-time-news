import React, { useState } from "react";
import { useNavigate } from "react-router-dom"
import "./NewsFileViewer.css";

function NewsFileViewer() {
  const BASE_URL = import.meta.env.VITE_BASE_URL
  const navigate = useNavigate();
  const [newsCards, setNewsCards] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // const parseNewsFile = (rawText) => {
  //   const articles = rawText.split("-".repeat(100)).map((block) => {
  //     const lines = block.trim().split("\n");
  //     const article = {};

  //     lines.forEach((line) => {
  //       if (line.startsWith("News Category:")) {
  //         article.category = line.replace("News Category:", "").trim();
  //       } else if (line.startsWith("Headline:")) {
  //         article.headline = line.replace("Headline:", "").trim();
  //       } else if (line.startsWith("Source:")) {
  //         article.source = line.replace("Source:", "").trim();
  //       } else if (line.startsWith("URL:")) {
  //         article.url = line.replace("URL:", "").trim();
  //       } else if (line.startsWith("Published Date:")) {
  //         article.pubDate = line.replace("Published Date:", "").trim();
  //       } else if (line.startsWith("Severity:")) {
  //         article.severity = line.replace("Severity:", "").trim();
  //       } else if (line.startsWith("Content:")) {
  //         article.content = line.replace("Content:", "").trim();
  //       } else if (article.content !== undefined) {
  //         article.content += "\n" + line.trim();
  //       }
  //     });

  //     return article;
  //   });

  //   // Filter out empty blocks
  //   return articles.filter((art) => art.headline);
  // };

  const fetchNewsFile = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${BASE_URL}/recent-published-articles`);
      const data = await response.json();

      if (data.status === "success") {
        setNewsCards(data.articles || []);
      } else {
        setError(data.message || "Error fetching news");
      }
    } catch (err) {
      console.error("Error fetching news:", err);
      setError("Failed to connect to server");
    }
    setLoading(false);
  };

  const downloadPDF = async () => {
    try {
      const response = await fetch(`${BASE_URL}/generate-pdf`, {
        method: "GET",
      });

      if (!response.ok) {
        throw new Error("Failed to download PDF");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute(
        "download",
        `daily_governance_report_${new Date().toISOString().slice(0, 10)}.pdf`
      );

      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (err) {
      console.error("Error downloading PDF:", err);
      setError("Failed to download PDF");
    }
  };

  return (
    <div className="news-viewer-container">
      <div className="header-section">
        <div className="government-seal">
          <div className="seal-icon">🏛️</div>
        </div>
        <h1 className="main-title">Daily Governance Report</h1>
        <p className="subtitle">Official Government News & Updates</p>
      </div>

      <div className="action-bar">
        <button onClick={fetchNewsFile} className="btn btn-primary2" disabled={loading}>
          <span className="btn-icon">📰</span>
          Fetch Latest News
        </button>

        <button onClick={downloadPDF} className="btn btn-secondary" disabled={loading}>
          <span className="btn-icon">📄</span>
          Download PDF Report
        </button>
        
        <button onClick={() => navigate("/calender")} className="btn btn-secondary2" disabled={loading}>
          <span className="btn-icon">📰</span>
          Get Articles by Date
        </button>
      </div>

      {loading && (
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p className="loading-text">Loading latest governance updates...</p>
        </div>
      )}

      {error && (
        <div className="error-container">
          <div className="error-icon">⚠️</div>
          <p className="error-text">{error}</p>
        </div>
      )}

      <div className="news-grid">
        {newsCards.map((article, index) => (
          <div key={index} className="news-card">
            <div className="card-header">
              <h3 className="article-headline">{article.headline}</h3>
              {/* <div className="article-meta">
                <span className="meta-item">
                  <strong>Category:</strong> {article.category}
                </span>
                <span className="meta-item">
                  <strong>Source:</strong> {article.source}
                </span>
                <span className="meta-item">
                  <strong>Published:</strong> {article.pubDate}
                </span>
                <span className="meta-item severity">
                  <strong>Priority:</strong>
                  <span className={`severity-badge ${article.severity?.toLowerCase()}`}>
                    {article.severity}
                  </span>
                </span>
              </div> */}
            </div>

            <div className="card-content">
              <p className="article-content">{article.content || article.description}</p>
            </div>

            <div className="card-content">
              <h3>Issue</h3>
              <p className="article-content">{article.issue_reason}</p>
            </div>

            {article.url && (
              <div className="card-footer">
                <a 
                  href={article.url} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="source-link"
                >
                  View Original Source →
                </a>
              </div>
            )}
          </div>
        ))}
      </div>

      {newsCards.length === 0 && !loading && !error && (
        <div className="empty-state">
          <div className="empty-icon">📋</div>
          <h3>No Reports Available</h3>
          <p>Click "Fetch Latest News" to load the most recent governance updates.</p>
        </div>
      )}
    </div>
  );
}

export default NewsFileViewer;