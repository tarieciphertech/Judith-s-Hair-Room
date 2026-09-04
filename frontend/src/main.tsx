import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import './styles.css'
import App from './App'
import Booking from './Booking'
import Confirmation from './Confirmation'

const restoreGitHubPagesRoute = () => {
  const pending = sessionStorage.getItem('judith_pending_route')
  if (pending && window.location.pathname === '/') {
    sessionStorage.removeItem('judith_pending_route')
    window.history.replaceState({}, '', pending)
  }
}
restoreGitHubPagesRoute()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/booking" element={<Booking />} />
        <Route path="/booking/confirmation" element={<Confirmation />} />
        <Route path="*" element={<App />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
