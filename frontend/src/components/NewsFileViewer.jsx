import React, { useState, useEffect } from "react";
import Modal from './Modal';
import { useNavigate } from "react-router-dom";
import "./NewsFileViewer.css";
import Footer from "./Footer";

function NewsFileViewer() {
  const BASE_URL = import.meta.env.VITE_BASE_URL;
  const navigate = useNavigate();
  const [newsCards, setNewsCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [modalContent, setModalContent] = useState("");
  // const [isSearching, setIsSearching] = useState(false);

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

  const handleSearch = async () => {
    console.log("Searching...");
  };


  const fetchNewsFile = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${BASE_URL}/recent-published-articles`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.status === "success") {
        setNewsCards(data.articles || []);
        if (data.articles && data.articles.length === 0) {
          setError("No articles available at the moment");
        }
      } else {
        setError(data.message || "Error fetching news");
      }
    } catch (err) {
      console.error("Error fetching news:", err);
      setError("Failed to connect to server. Please check your connection.");
      setNewsCards([]);
    } finally {
      setLoading(false);
    }
  };

  const downloadPDF = async () => {
    setIsDownloading(true);
    setError("");
    try {
      const response = await fetch(`${BASE_URL}/generate-pdf`, {
        method: "GET",
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
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
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Error downloading PDF:", err);
      setError("Failed to download PDF. Please try again.");
    } finally {
      setIsDownloading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/");
  };

  const refreshNews = () => {
    fetchNewsFile();
  };

  useEffect(() => {
    fetchNewsFile();
    
    // Auto-refresh every 10 minutes
    const interval = setInterval(fetchNewsFile, 10 * 60 * 1000);
    
    return () => clearInterval(interval);
  }, [BASE_URL]);

  useEffect(() => {
    setCurrentPage(1); // Reset to first page when new data arrives
  }, [newsCards]);

  // Pagination calculations
  const indexOfLastArticle = currentPage * articlesPerPage;
  const indexOfFirstArticle = indexOfLastArticle - articlesPerPage;
  const currentArticles = newsCards.slice(indexOfFirstArticle, indexOfLastArticle);
  const totalPages = Math.ceil(newsCards.length / articlesPerPage);

  // Format date for display
  const formatDate = (dateString) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (error) {
      console.error("Error formatting date:", error);
      return dateString;
    }
  };

  return (
    <div className="news-viewer-container">
      <div className="header-section">
        <div className="government-seal">
          <div className="seal-icon">🏛</div>
        </div>
        <h1 className="main-title">Daily Governance Report</h1>
        <p className="subtitle">Official Government News & Updates Portal</p>
      </div>

      <div className="action-bar">
        <button 
          onClick={refreshNews} 
          className="btn btn-secondary2" 
          disabled={loading}
        >
          {loading ? <div className="btn-loader"></div> : <span className="btn-icon">🔄</span>}
          {loading ? "Refreshing..." : "Refresh News"}
        </button>

        <button 
          onClick={downloadPDF} 
          className="btn btn-secondary2" 
          disabled={loading || isDownloading || newsCards.length === 0}
        >
          {isDownloading ? <div className="btn-loader"></div> : <span className="btn-icon">📰</span>}
          {isDownloading ? "Downloading..." : "Download PDF Report"}
        </button>

        <button 
          onClick={() => navigate("/calender")} 
          className="btn btn-secondary3" 
          disabled={loading}
        >
          <span className="btn-icon">📅</span>
          Get Articles by Date
        </button>

        <button 
          onClick={handleSearch} 
          className="btn btn-search" 
          disabled={loading}
        >
          <span className="btn-icon">🔍</span>
          Search Articles
        </button>

        <button 
          onClick={handleLogout} 
          className="btn btn-third" 
          disabled={loading}
        >
          <span className="btn-icon">🚪</span>
          Log out
        </button>
      </div>

      {loading && (
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p className="loading-text">Loading latest governance updates...</p>
        </div>
      )}

      {error && !loading && (
        <div className="error-container">
          <div className="error-icon">⚠</div>
          <p className="error-text">{error}</p>
          <button 
            onClick={refreshNews} 
            className="btn btn-secondary2" 
            style={{ marginTop: '15px' }}
          >
            <span className="btn-icon">🔄</span>
            Try Again
          </button>
        </div>
      )}

      {!loading && !error && (
        <>
          <h1 className="todays-news-title">
            Today's News ({newsCards.length} {newsCards.length === 1 ? 'Article' : 'Articles'})
          </h1>

          {newsCards.length > 0 ? (
            <>
              <div className="news-grid">
                {currentArticles.map((article, index) => (
                  <div key={article.id || index} className="news-card">
                    <div className="card-header">
                      <h3 className="article-headline">
                        {article.headline_ai || article.title || 'No Title Available'}
                      </h3>
                      <span className="article-date">
                        {formatDate(article.published_date || article.date || new Date().toISOString())}
                      </span>
                    </div>
                    <div className="card-content">
                      <h3>Issue</h3>
                      <p
                        className="article-content"
                        dangerouslySetInnerHTML={{
                          __html: (article.issue_reason || article.summary || article.description || 'No description available')
                            .replace(/^\./, "").trim(),
                        }}
                      ></p>
                    </div>
                    <div className="card-footer">
                      {(article.content || article.full_content || article.body) && (
                        <a
                          onClick={() => openModal(
                            article.content || 
                            article.full_content || 
                            article.body || 
                            article.description || 
                            'No detailed content available'
                          )}
                          className="source-link"
                          style={{ cursor: 'pointer' }}
                        >
                          📖 View Detailed Source
                        </a>
                      )}
                      {article.url && (
                        <a
                          href={article.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="source-link"
                        >
                          🔗 View Original Source
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>

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
            </>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">📋</div>
              <h3>No Reports Available</h3>
              <p>
                There are no reports to display at the moment. New reports will
                appear here automatically.
              </p>
              <button 
                onClick={refreshNews} 
                className="btn btn-secondary2" 
                style={{ marginTop: '20px' }}
              >
                <span className="btn-icon">🔄</span>
                Refresh
              </button>
            </div>
          )}
        </>
      )}

      <Footer />

      {showModal && (
        <Modal onClose={closeModal}>
          <div style={{ maxHeight: '70vh', overflowY: 'auto' }}>
            <h2 style={{ 
              marginBottom: '20px', 
              color: '#1e40af', 
              borderBottom: '2px solid #e5e7eb', 
              paddingBottom: '10px' 
            }}>
              Detailed Article Content
            </h2>
            <div 
              className="modal-content-text" 
              style={{ lineHeight: '1.8', fontSize: '16px' }}
              dangerouslySetInnerHTML={{ __html: modalContent }}
            />
          </div>
        </Modal>
      )}

    </div>
  );
}

export default NewsFileViewer;