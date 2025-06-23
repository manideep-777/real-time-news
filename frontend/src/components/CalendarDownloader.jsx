
import { useState, useEffect } from "react"
import "./CalendarDownloader.css"
import { toast } from "react-hot-toast"
import { useNavigate } from "react-router-dom"

const CalendarDownloader = () => {
  const navigate = useNavigate();
  const BASE_URL = import.meta.env.VITE_BASE_URL
  const [selectedDate, setSelectedDate] = useState("")
  const [articles, setArticles] = useState([])

  // Set default to today's date
  useEffect(() => {
    const today = new Date().toISOString().split("T")[0]
    setSelectedDate(today)
  }, [])

  const handleDownload = async (e) => {
    e.preventDefault()
    if (!selectedDate) {
      toast.error("Please select a valid date.")
      return
    }

    const downloadUrl = `${BASE_URL}/generate-pdf-by-date?date=${selectedDate}`

    try {
      const response = await fetch(downloadUrl, { method: "HEAD" })

      if (!response.ok) {
        toast.error(`No report found for ${selectedDate}`)
        return
      }

      window.location.href = downloadUrl
    } catch (error) {
      console.error("Download error:", error)
      toast.error("An error occurred while trying to download the report.")
    }
  }

  const handleFetchNews = async () => {
    if (!selectedDate) {
      alert("Please select a valid date.")
      return
    }

    const fetchUrl = `${BASE_URL}/published-articles-by-date?date=${selectedDate}`

    try {
      const response = await fetch(fetchUrl)
      const result = await response.json()

      if (result.status === "success") {
        setArticles(result.articles || [])
        toast.success(`✅ ${result.message || "News fetched successfully."}`)
      } else {
        toast.error("❌ Failed to fetch news: " + result.message)
      }
    } catch (error) {
      console.error("Fetch error:", error)
      toast.error("❌ An error occurred while fetching news.")
    }
  }

  const formatDate = (dateString) => {
    const options = { year: "numeric", month: "long", day: "numeric" }
    return new Date(dateString).toLocaleDateString("en-US", options)
  }

  const handleLogout = () => {
    localStorage.removeItem("token")
    navigate("/")
  }

  return (
    <div className="dashboard-container">
      {/* Header Section */}
      <div className="header-section">
        <div className="government-icon">
          {/* <svg width="60" height="60" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 3L2 9V11H22V9L12 3Z" fill="currentColor" opacity="0.7" />
            <path d="M4 11V19H6V11H4Z" fill="currentColor" />
            <path d="M8 11V19H10V11H8Z" fill="currentColor" />
            <path d="M12 11V19H14V11H12Z" fill="currentColor" />
            <path d="M16 11V19H18V11H16Z" fill="currentColor" />
            <path d="M20 11V19H22V11H20Z" fill="currentColor" />
            <path d="M2 19H22V21H2V19Z" fill="currentColor" />
          </svg> */}
          <div className="seal-icon">🏛️</div>
        </div>
        <h1 className="main-title">Daily Governance Report</h1>
        <p className="subtitle">Official Government News & Updates</p>
      </div>

      {/* Date Selection and Action Buttons */}
      <div className="action-section">
        <div className="date-selector">
          <label htmlFor="date-input" className="date-label">
            Select Date:
          </label>
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
          <button type="button" onClick={handleFetchNews} className="btn btn-fetch">
            <span className="btn-icon">📰</span>
            Fetch News
          </button>

          <button type="button" onClick={handleDownload} className="btn btn-download">
            <span className="btn-icon">📄</span>
            Download PDF Report
          </button>

          <button onClick={handleLogout} className="btn btn-third">
            Log out
          </button>
        </div>
      </div>

      {/* News Articles Section */}
      {articles.length > 0 && (
        <div className="news-section">
          <div className="news-header">
            <h2 className="news-title">📰 News Articles for {formatDate(selectedDate)}</h2>
            <p className="news-count">{articles.length} articles found</p>
          </div>

          <div className="articles-grid">
            {articles.map((article, index) => (
              <div key={index} className="article-card">
                <div className="article-header">
                  <h3 className="article-headline">{article.headline}</h3>
                  <span className="article-date">{article.published_date}</span>
                </div>

                <div className="article-content">
                  <p className="article-summary">
                    {article.content || article.description || "Click to read the full article for more details."}
                  </p>
                </div>

                <div className="article-content">
                  <h3>Issue</h3>
                  <p className="article-summary">{article.issue_reason}</p>
                </div>

                <div className="article-footer">
                  <a href={article.url} target="_blank" rel="noopener noreferrer" className="read-more-link">
                    Read Full Article →
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {articles.length === 0 && selectedDate && (
        <div className="empty-state">
          <div className="empty-icon">📅</div>
          <h3>No articles loaded yet</h3>
          <p>Select a date and click "Fetch Latest News" to view articles</p>
        </div>
      )}
    </div>
  )
}

export default CalendarDownloader
