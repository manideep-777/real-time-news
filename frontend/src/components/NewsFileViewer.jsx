import React, { useState, useEffect } from "react";
import Modal from './Modal';
import { useNavigate } from "react-router-dom";
import "./NewsFileViewer.css";
import Footer from "./Footer";

function NewsFileViewer() {
  const BASE_URL = import.meta.env.VITE_BASE_URL;
  const navigate = useNavigate();
  const [newsCards, setNewsCards] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [modalContent, setModalContent] = useState("");

  const [currentPage, setCurrentPage] = useState(1);
  const articlesPerPage = 9;

  const openModal = (content) => {
    setModalContent(content);
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setModalContent("");
  };

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
    setIsDownloading(true);
    setError("");
    try {
      const response = await fetch(`${BASE_URL}/generate-pdf`, {
        method: "GET",
        headers: {
          Accept: "application/pdf",
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });

      if (!response.ok) throw new Error("Failed to download PDF");

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
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Error downloading PDF:", err);
      setError("Failed to download PDF");
    } finally {
      setIsDownloading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/");
  };

  useEffect(() => {
    fetchNewsFile();
    const interval = setInterval(fetchNewsFile, 10 * 60 * 1000); // 10 mins
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    setCurrentPage(1); // reset page if new data comes in
  }, [newsCards]);

  const indexOfLastArticle = currentPage * articlesPerPage;
  const indexOfFirstArticle = indexOfLastArticle - articlesPerPage;
  const currentArticles = newsCards.slice(indexOfFirstArticle, indexOfLastArticle);
  const totalPages = Math.ceil(newsCards.length / articlesPerPage);

  return (
    <div className="news-viewer-container">
      <div className="header-section">
        <div className="government-seal">
          <div className="seal-icon">🏛</div>
        </div>
        <h1 className="main-title">Daily Governance Report</h1>
        <p className="subtitle">Official Government News & Updates</p>
      </div>

      <div className="action-bar">
        <button onClick={downloadPDF} className="btn btn-secondary2" disabled={loading || isDownloading}>
          {isDownloading ? <div className="btn-loader"></div> : <span className="btn-icon">📰</span>}
          {isDownloading ? "Downloading..." : "Download PDF Report"}
        </button>

        <button onClick={() => navigate("/calender")} className="btn btn-secondary3" disabled={loading}>
          <span className="btn-icon">📅</span>
          Get Articles by Date
        </button>

        <button onClick={handleLogout} className="btn btn-third" disabled={loading}>
          Log out
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
          <div className="error-icon">⚠</div>
          <p className="error-text">{error}</p>
        </div>
      )}

      <h1 style={{ padding: "10px", fontSize: "40px" }}>Today's news</h1>

      <div className="news-grid">
        {currentArticles.map((article, index) => (
          <div key={index} className="news-card">
            <div className="card-header">
              {console.log(article)}
              <h3 className="article-headline">{article.headline_ai}</h3>
              <span className="article-date">{article.published_date}</span>
            </div>
            <div className="card-content">
              <h3>Issue</h3>
              <p
                className="article-content"
                dangerouslySetInnerHTML={{
                  __html: article.issue_reason?.replace(/^\./, "").trim(),
                }}
              ></p>
            </div>
            <div className="card-footer">
              <a
                onClick={() => openModal(article.content || article.description)}
                className="source-link"
                style={{ marginLeft: "10px" }}
              >
                View Detailed Source
              </a>
              {article.url && (
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="source-link"
                >
                  View Original Source →
                </a>
              )}
            </div>
          </div>
        ))}
      </div>

      {newsCards.length === 0 && !loading && !error && (
        <div className="empty-state">
          <div className="empty-icon">📋</div>
          <h3>No Reports Available</h3>
          <p>
            There are no reports to display at the moment. New reports will
            appear here automatically.
          </p>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="pagination">
          <button
            className="pagination-btn"
            onClick={() => setCurrentPage((prev) => prev - 1)}
            disabled={currentPage === 1}
          >
            ⬅ Prev
          </button>

          {/* Always show first page */}
          <button
            className={`pagination-btn ${currentPage === 1 ? "active" : ""}`}
            onClick={() => setCurrentPage(1)}
          >
            1
          </button>

          {/* Show left dots if needed */}
          {currentPage > 3 && totalPages > 5 && <span>...</span>}

          {/* Pages around current */}
          {Array.from({ length: totalPages }, (_, i) => i + 1)
            .filter((page) => {
              if (page === 1 || page === totalPages) return false;
              if (currentPage <= 3) return page <= 4;
              if (currentPage >= totalPages - 2) return page >= totalPages - 3;
              return Math.abs(page - currentPage) <= 1;
            })
            .map((page) => (
              <button
                key={page}
                className={`pagination-btn ${currentPage === page ? "active" : ""}`}
                onClick={() => setCurrentPage(page)}
              >
                {page}
              </button>
            ))}

          {/* Show right dots if needed */}
          {currentPage < totalPages - 2 && totalPages > 5 && <span>...</span>}

          {/* Always show last page if not shown */}
          {totalPages > 1 && (
            <button
              className={`pagination-btn ${currentPage === totalPages ? "active" : ""}`}
              onClick={() => setCurrentPage(totalPages)}
            >
              {totalPages}
            </button>
          )}

          <button
            className="pagination-btn"
            onClick={() => setCurrentPage((prev) => prev + 1)}
            disabled={currentPage === totalPages}
          >
            Next ➡
          </button>
        </div>
      )}
      <Footer />

      {showModal && (
        <Modal onClose={closeModal}>
          <p className="modal-content-text">{modalContent}</p>
        </Modal>
      )}
    </div>

  );
}

export default NewsFileViewer;