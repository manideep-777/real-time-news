import { useNavigate } from "react-router-dom"
import { useState } from "react"
import { toast } from "react-hot-toast"
import "./Authentcation.css"

const Authentication = () => {
  const BASE_URL = import.meta.env.VITE_BASE_URL
    const navigate = useNavigate();
  // const [signupData, setSignupData] = useState({
  //   fullName: "",
  //   email: "",
  //   password: "",
  //   confirmPassword: "",
  // })

  const [loginData, setLoginData] = useState({
    email: "",
    password: "",
  })

  // const handleSignupChange = (e) => {
  //   setSignupData({
  //     ...signupData,
  //     [e.target.name]: e.target.value,
  //   })
  // }

  const handleLoginChange = (e) => {
    setLoginData({
      ...loginData,
      [e.target.name]: e.target.value,
    })
  }

  // const handleSignupSubmit = async (e) => {
  //   e.preventDefault()
  
  //   if (signupData.password !== signupData.confirmPassword) {
  //     toast.error("Passwords do not match")
  //     return
  //   }
  
  //   try {
  //     const res = await fetch(`${BASE_URL}/signup`, {
  //       method: "POST",
  //       headers: { "Content-Type": "application/json" },
  //       body: JSON.stringify(signupData),
  //     })
  //     const data = await res.json()
  
  //     if (data.status === "success") {
  //       localStorage.setItem("token", data.token)
  //       toast.success("Signup successful!")
  //       navigate("/dashboard")
  //     } else {
  //       toast.error(data.message || "Signup failed")
  //     }
  //   } catch (err) {
  //       toast.error(`Server error ${err}`)
  //   }
  // }

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
            
            
          </div>
        </div> 

        {/* Vertical Separator */}
        {/* <div className="separator">
          <div className="separator-line"></div>
          <span className="separator-text">or</span>
          <div className="separator-line"></div>
        </div> */}

        {/* Login Section - Right Side */}
        <div className="auth-section login-section">
          <div className="auth-form">
            <h2 className="auth-title">Welcome Back</h2>
            <p className="auth-subtitle">Sign in to your account</p>

            <form onSubmit={handleLoginSubmit} className="form">
              <div className="input-group">
                <label htmlFor="login-email" className="label">
                  Email Address
                </label>
                <input
                  type="email"
                  id="login-email"
                  name="email"
                  value={loginData.email}
                  onChange={handleLoginChange}
                  className="input"
                  placeholder="Enter your email"
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
