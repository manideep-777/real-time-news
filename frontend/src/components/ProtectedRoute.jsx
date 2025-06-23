import { useEffect, useState } from "react"
import { Navigate } from "react-router-dom"
import { toast } from "react-hot-toast"

const BASE_URL = import.meta.env.VITE_BASE_URL // update if different

const ProtectedRoute = ({ children }) => {
  const [auth, setAuth] = useState(null)

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const res = await fetch(`${BASE_URL}/is-authenticated`, {
          method: "GET",
          headers: {
            Authorization: localStorage.getItem("token"),
          },
        })
        const data = await res.json()
        if (!data.authenticated) {
          toast.error("Please login to continue")
          setAuth(false)
        } else {
          setAuth(true)
        }
        console.log(data) // log the response t
      } catch {
        toast.error("Auth check failed. Please login.")
        setAuth(false)
      }
    }

    checkAuth()
  }, [])

  if (auth === null) return <p>Checking auth...</p>
  if (!auth) return <Navigate to="/" />
  return children
}

export default ProtectedRoute
