//test for the search component using json file

import { useState, useEffect } from "react";
import "./search.css";
import { toast } from "react-hot-toast";

const Search = () => {
  const [query, setQuery] = useState("");
  // const [allArticles, setAllArticles] = useState([]);
  const [articles, setArticles] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const articlesPerPage = 9;

  useEffect(() => {
    const delay = setTimeout(async () => {
      if (query.trim().length > 1) {
        try {
          const res = await fetch(`${import.meta.env.VITE_BASE_URL}/search-articles?keyword=${encodeURIComponent(query.trim())}`);
          const data = await res.json();

          if (data.status === "success") {
            setArticles(data.articles || []);
            setCurrentPage(1);

            if (data.articles.length > 0) {
              toast.success(`${data.articles.length} articles found`);
            } else {
              toast.error("No matching articles.");
            }
          } else {
            toast.error(data.message || "Search failed.");
          }
        } catch (err) {
          toast.error("Error fetching search results.");
          console.error(err);
        }
      }
    }, 500);

    return () => clearTimeout(delay);
  }, [query]);


  const totalPages = Math.ceil(articles.length / articlesPerPage);
  const paginatedArticles = articles.slice(
    (currentPage - 1) * articlesPerPage,
    currentPage * articlesPerPage
  );

  return (
    <div className="search-container">
      <h2 className="search-title">Search Articles</h2>

      <form
        onSubmit={(e) => {
          e.preventDefault();
        }}
        className="search-bar"
      >
        <div className="search-input-btn">
          <div style={{"padding-right":"20px"}}>
            <input
              type="text"
              placeholder="Enter keyword to search..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="search-input"
            />
          </div>
          <div>
            <button type="submit" className="btn btn-search">
              Search
            </button>
          </div>
        </div>
      </form>

      {articles.length > 0 && (
        <p style={{ textAlign: "center", fontWeight: 500, "padding-bottom":"20px" }}>
          {articles.length} articles found for "{query}"
        </p>
      )}

      <div className="results-grid">
        {paginatedArticles.length === 0 ? (
          <p>No results to display</p>
        ) : (
          paginatedArticles.map((article, idx) => (
            <div key={idx} className="news-card">
              <div className="card-header">
                <h3>{article.headline_ai || article.headline || "Untitled Article"}</h3>
                <span className="article-date">
                  {article.published_date
                    ? new Date(article.published_date).toLocaleString()
                    : "Unknown Date"}
                </span>
              </div>

              <div className="card-content">
                <p>
                  {article.content?.slice(0, 250) ||
                    article.issue_reason || article.description ||
                    "No content available."}
                </p>
              </div>

              <div className="card-footer">
                {article.url && (
                  <a
                    className="source-link"
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View Full Article →
                  </a>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          {Array.from({ length: totalPages }, (_, i) => (
            <button
              key={i}
              className={`page-btn ${currentPage === i + 1 ? "active" : ""}`}
              onClick={() => setCurrentPage(i + 1)}
            >
              {i + 1}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default Search;