import { useState, useEffect } from "react";
import "./CalendarDownloader.css";  
import { toast } from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import Modal from './Modal';
import Footer from "./Footer";

const CalendarDownloader = () => {
  const navigate = useNavigate();
  const BASE_URL = import.meta.env.VITE_BASE_URL;
  const [selectedDate, setSelectedDate] = useState("");
  const [articles, setArticles] = useState([]);
  const [isDownloading, setIsDownloading] = useState(false);
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

  useEffect(() => {
    const today = new Date().toISOString().split("T")[0];
    setSelectedDate(today);
  }, []);

  useEffect(() => {
    if (selectedDate) {
      handleFetchNews();
    }
  }, [selectedDate]);

  const handleDownload = async (e) => {
    e.preventDefault();
    if (!selectedDate) {
      toast.error("Please select a valid date.");
      return;
    }

    setIsDownloading(true);
    const downloadUrl =`${BASE_URL}/generate-pdf-by-date?date=${selectedDate}`;

    try {
      const response = await fetch(downloadUrl);

      if (!response.ok) {
        toast.error(`No report found for ${selectedDate}`);
        return;
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download",`daily_governance_report_${selectedDate}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Download error:", error);
      toast.error("An error occurred while trying to download the report.");
    } finally {
      setIsDownloading(false);
    }
  };

  const handleFetchNews = async () => {
    if (!selectedDate) {
      alert("Please select a valid date.");
      return;
    }

    const fetchUrl = `${BASE_URL}/published-articles-by-date?date=${selectedDate}`;

    try {
      const response = await fetch(fetchUrl);
      const result = await response.json();

      if (result.status === "success") {
        setArticles(result.articles || []);
        setCurrentPage(1);
        toast.success(`✅ ${result.message || "News fetched successfully."}`);
      } else {
        toast.error("❌ Failed to fetch news: " + result.message);
      }
    } catch (error) {
      console.error("Fetch error:", error);
      toast.error("❌ An error occurred while fetching news.");
    }
  };

  const formatDate = (dateString) => {
    const options = { year: "numeric", month: "long", day: "numeric" };
    return new Date(dateString).toLocaleDateString("en-US", options);
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/");
  };

  const handleBack = () => {
    navigate(-1);
  };

  const totalPages = Math.ceil(articles.length / articlesPerPage);
  const paginatedArticles = articles.slice(
    (currentPage - 1) * articlesPerPage,
    currentPage * articlesPerPage
  );

  return (
    <div className="dashboard-container">
      {/* Header */}
      <div className="header-section">
        <button onClick={handleBack} className="btn btn-back">&#x2B05; Back</button>
        <div className="government-icon"><div className="seal-icon">🏛</div></div>
        <h1 className="main-title">Daily Governance Report</h1>
        <p className="subtitle">Official Government News & Updates</p>
      </div>

      {/* Actions */}
      <div className="action-section">
        <div className="date-selector">
          <label htmlFor="date-input" className="date-label">Select Date:</label>
          <input
            id="date-input"
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="date-input"
            required
          />
        </div>

        <div className="button-group">
          <button type="button" onClick={handleDownload} className="btn btn-download" disabled={isDownloading}>
            {isDownloading ? <div className="btn-loader"></div> : <span className="btn-icon">📄</span>}
            {isDownloading ? "Downloading..." : "Download PDF Report"}
          </button>
          <button onClick={handleLogout} className="btn btn-third">Log out</button>
        </div>
      </div>

      {/* Articles */}
      {paginatedArticles.length > 0 && (
        <div className="news-section">
          <div className="news-header">
            <h2 className="news-title"> News Articles for {formatDate(selectedDate)}</h2>
            <p className="news-count">{articles.length} articles found</p>
          </div>

          <div className="articles-grid">
            {paginatedArticles.map((article, index) => (
              <div key={index} className="article-card">
                <div className="article-header">
                  <h3 className="article-headline">{article.headline_ai}</h3>
                  <span className="article-date">{article.published_date}</span>
                </div>
                <div className="article-content">
                  <h3>Issue</h3>
                  <p className="article-summary">{article.issue_reason?.replace(/^\./, "").trim()}</p>
                </div>
                <div className="article-footer">
                  <div className="footer-links">
                    <a
                      onClick={() => openModal(article.content || article.description)}
                      className="source-link"
                    >
                      View Detailed Source
                    </a>
                    <a
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="read-more-link"
                    >
                      Read Full Article →
                    </a>
                  </div>
                </div>


              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="pagination">
              <button className="pagination-btn" onClick={() => setCurrentPage((p) => p - 1)} disabled={currentPage === 1}>
                ⬅ Prev
              </button>

              <button className={`pagination-btn ${currentPage === 1 ? "active" : ""}`} onClick={() => setCurrentPage(1)}>
                1
              </button>

              {currentPage > 3 && totalPages > 5 && <span className="dots">...</span>}

              {Array.from({ length: totalPages }, (_, i) => i + 1)
                .filter((page) => {
                  if (page === 1 || page === totalPages) return false;
                  if (currentPage <= 3) return page <= 4;
                  if (currentPage >= totalPages - 2) return page >= totalPages - 3;
                  return Math.abs(page - currentPage) <= 1;
                })
                .map((page) => (
                  <button key={page} className={`pagination-btn ${currentPage === page ? "active" : ""}`} onClick={() => setCurrentPage(page)}>
                    {page}
                  </button>
                ))}

              {currentPage < totalPages - 2 && totalPages > 5 && <span className="dots">...</span>}

              {totalPages > 1 && (
                <button className={`pagination-btn ${currentPage === totalPages ? "active" : ""}`} onClick={() => setCurrentPage(totalPages)}>
                  {totalPages}
                </button>
              )}

              <button className="pagination-btn" onClick={() => setCurrentPage((p) => p + 1)} disabled={currentPage === totalPages}>
                Next ➡
              </button>
            </div>
          )}
        </div>
      )}

      {/* Footer */}
      <Footer />

      {/* Empty State */}
      {articles.length === 0 && selectedDate && (
        <div className="empty-state">
          <div className="empty-icon">📅</div>
          <h3>No articles found</h3>
          <p>For the selected date {selectedDate}, no articles were found.</p>
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <Modal onClose={closeModal}>
          <p className="modal-content-text">{modalContent}</p>
        </Modal>
      )}
    </div>
  );
};

export default CalendarDownloader;