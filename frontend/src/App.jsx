import { Routes, Route } from 'react-router-dom';
import { Toaster } from "react-hot-toast"

import NewsFileViewer from './components/NewsFileViewer'
import './App.css'
import Authentcation from './components/Authentcation';
import CalendarDownloader from './components/CalendarDownloader';
function App() {

  return (
    <>
    <Routes>
      <Route path="/" element={<Authentcation />} />
      <Route path="/dashboard" element={<NewsFileViewer />} />
      <Route path="/calender" element={<CalendarDownloader />} />
    </Routes>
    <Toaster position="top-right" toastOptions={{ duration: 3000 }} />
    </>
  )
}

export default App
