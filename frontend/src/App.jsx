import { Routes, Route } from 'react-router-dom';
import { Toaster } from "react-hot-toast"

import NewsFileViewer from './components/NewsFileViewer'
import './App.css'
import Authentication from './components/Authentcation';
import CalendarDownloader from './components/CalendarDownloader';
import ProtectedRoute from "./components/ProtectedRoute"
import Search from './components/Search';
function App() {

  return (
    <>
      <Routes>
        <Route path="/" element={<Authentication />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <NewsFileViewer />
            </ProtectedRoute>
          }
        />
        <Route
          path="/calender"
          element={
            <ProtectedRoute>
              <CalendarDownloader />
            </ProtectedRoute>
          }
        />
        <Route
          path="/search"
          element={
            <ProtectedRoute>
              <Search />
            </ProtectedRoute>
          }
        />
      </Routes>
      <Toaster position="top-right" toastOptions={{ duration: 3000 }} />
    </>
  )
}

export default App
