import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Authentcation.css";
import logo from "../assets/ap-logo.png";
import { toast } from "react-hot-toast"

const Authentication = () => {
  const [loginData, setLoginData] = useState({ username: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const BASE_URL = import.meta.env.VITE_BASE_URL
  const navigate = useNavigate();

  const handleChange = (e) => {
    setLoginData({ ...loginData, [e.target.name]: e.target.value });
  };

  
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
    <div className="login-container">
      <div className="login-wrapper">
        {/* Left Section */}
        <div className="login-left">
          <img src={logo} alt="AP Logo" className="ap-logo" />
          <h1>Real Time Governance</h1>
          <p>
            Secure, transparent, and efficient governance solutions powered by
            cutting-edge technology
          </p>
          <div className="dots">
            <span className="dot active" />
            <span className="dot" />
            <span className="dot" />
          </div>
          <small>
            Join thousands of organizations transforming their governance
            processes
          </small>
        </div>

        {/* Right Section */}
        <div className="login-right">
          <h2>Welcome Back</h2>
          <p>Please sign in to your account</p>

          <form onSubmit={handleLoginSubmit}>
            <label>Username</label>
            <input
              type="text"
              name="username"
              placeholder="Enter your username"
              value={loginData.username}
              onChange={handleChange}
              required
            />

            <label>Password</label>
            <div className="password-box">
              <input
                type={showPassword ? "text" : "password"}
                name="password"
                placeholder="Enter your password"
                value={loginData.password}
                onChange={handleChange}
                required
              />
              <button
                type="button"
                className="toggle-password"
                onClick={() => setShowPassword(!showPassword)}
              >
                👁
              </button>
            </div>

            <button type="submit" className="sign-in-btn">
              Sign In
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Authentication;
