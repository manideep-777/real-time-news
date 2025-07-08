import { useNavigate } from "react-router-dom"
import { useState } from "react"
import { toast } from "react-hot-toast"
import "./Authentcation.css"
import logo from "../assets/Daily-News.svg";

  // ✅ Import the logo

const Authentication = () => {
  const BASE_URL = import.meta.env.VITE_BASE_URL
  const navigate = useNavigate();

  const [loginData, setLoginData] = useState({
    username: "", 
    password: "",
  })

  const handleLoginChange = (e) => {
    setLoginData({
      ...loginData,
      [e.target.name]: e.target.value,
    })
  }

  const handleLoginSubmit = async (e) => {
    e.preventDefault()

    try {
      const res = await fetch(`${BASE_URL}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(loginData),
      })
      const data = await res.json()

      if (data.status === "success") {
        localStorage.setItem("token", data.token)
        toast.success("Login successful!")
        navigate("/dashboard")
      } else {
        toast.error(data.message || "Login failed")
      }
    } catch (err) {
      toast.error(`Server error ${err}`)
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-wrapper">
        {/* Sign Up Section - Left Side */}
        <div className="auth-section signup-section">
          <div className="auth-form">
            {/* ✅ Add logo here */}
            <img src={logo} alt="Real Time Governance Logo" className="auth-logo" style={{}} />
          </div>
        </div>

        {/* Login Section - Right Side */}
        <div className="auth-section login-section">
          <div className="auth-form">
            <h2 className="auth-title">Welcome Back</h2>
            <p className="auth-subtitle">Sign in to your account</p>

            <form onSubmit={handleLoginSubmit} className="form">
              <div className="input-group">
                <label htmlFor="login-email" className="label">
                  Username
                </label>
                <input
                  type="text"
                  id="login-email"
                  name="username"
                  value={loginData.username}
                  onChange={handleLoginChange}
                  className="input"
                  placeholder="Enter your Username"
                  required
                />
              </div>

              <div className="input-group">
                <label htmlFor="login-password" className="label">
                  Password
                </label>
                <input
                  type="password"
                  id="login-password"
                  name="password"
                  value={loginData.password}
                  onChange={handleLoginChange}
                  className="input"
                  placeholder="Enter your password"
                  required
                />
              </div>

              <button type="submit" className="btn btn-secondary">
                Sign In
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Authentication