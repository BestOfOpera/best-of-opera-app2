import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import NewProject from './pages/NewProject'
import ApproveOverlay from './pages/ApproveOverlay'
import ApprovePost from './pages/ApprovePost'
import ApproveYoutube from './pages/ApproveYoutube'
import Export from './pages/Export'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/new-project" element={<NewProject />} />
        <Route path="/project/:id/approve-overlay" element={<ApproveOverlay />} />
        <Route path="/project/:id/approve-post" element={<ApprovePost />} />
        <Route path="/project/:id/approve-youtube" element={<ApproveYoutube />} />
        <Route path="/project/:id/export" element={<Export />} />
      </Routes>
    </Layout>
  )
}
