import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./Authentcation.css";
import logo from "../assets/ap-logo.png";
import { toast } from "react-hot-toast"

const Authentication = () => {
  const [loginData, setLoginData] = useState({ username: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const BASE_URL = import.meta.env.VITE_BASE_URL
  const navigate = useNavigate();

  const [captcha, setCaptcha] = useState({ question: "", answer: 0 })
  const [captchaStatus, setCaptchaStatus] = useState(null)

  const handleChange = (e) => {
    const { name, value } = e.target;
    setLoginData((prev) => ({ ...prev, [name]: value }));
  
    if (name === "captchaInput") {
      if (value.length === 5) {
        if (value === captcha.answer) {
          setCaptchaStatus("correct");
        } else {
          setCaptchaStatus("incorrect");
        }
      } else {
        setCaptchaStatus(null);
      }
    }
  };
  

  const generateCaptcha = () => {
    const characters = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
    let captchaText = ''
    for (let i = 0; i < 5; i++) {
      captchaText += characters.charAt(Math.floor(Math.random() * characters.length))
    }
    setCaptcha({ question: captchaText, answer: captchaText })
    setCaptchaStatus(null)
  }

  useEffect(() => {
    generateCaptcha()
  }, [])

  const handleLoginSubmit = async (e) => {
    e.preventDefault()

    if (loginData.captchaInput !== captcha.answer) {
      toast.error("Captcha verification failed. Please try again.");
      generateCaptcha();
      setLoginData({ ...loginData, captchaInput: "" });
      setCaptchaStatus(null);
      return;
    }

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
          {/* <p>
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
          </small> */}
        </div>

        {/* Right Section */}
        <div className="login-right">
          <h2>Access Your Dashboard</h2>
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

            <div className="input-group">
              <label htmlFor="captcha" className="label">Captcha Verification</label>
              <div className="captcha-row">
                <div className="captcha-display">
                  <div className="captcha-text">{captcha.question}</div>
                </div>
                <button
                  type="button"
                  className="captcha-refresh"
                  onClick={() => {
                    generateCaptcha()
                    setLoginData({ ...loginData, captchaInput: "" })
                  }}
                  title="Generate new captcha"
                >
                  ↻
                </button>
                <input
                  type="text"
                  id="captcha"
                  name="captchaInput"
                  value={loginData.captchaInput}
                  onChange={handleChange}
                  className="input captcha-input-field"
                  placeholder="Enter"
                  maxLength="5"
                  required
                />
                <div className="captcha-status">
                  {captchaStatus === 'correct' && (
                    <span className="status-icon correct">✓</span>
                  )}
                  {captchaStatus === 'incorrect' && (
                    <span className="status-icon incorrect">✗</span>
                  )}
                </div>
              </div>
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
