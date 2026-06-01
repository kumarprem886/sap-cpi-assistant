import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import IFlowGenerator from './pages/IFlowGenerator'
import MessageMapping from './pages/MessageMapping'
import GroovyGenerator from './pages/GroovyGenerator'
import XSLTGenerator from './pages/XSLTGenerator'
import ChatAssistant from './pages/ChatAssistant'
import DocumentGenerator from './pages/DocumentGenerator'
import CPIConnect from './pages/CPIConnect'
import UserManagement from './pages/UserManagement'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter basename={import.meta.env.BASE_URL === '/sap-cpi-assistant/' ? '/sap-cpi-assistant' : ''}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={
            <ProtectedRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/iflow" element={<IFlowGenerator />} />
                  <Route path="/mapping" element={<MessageMapping />} />
                  <Route path="/groovy" element={<GroovyGenerator />} />
                  <Route path="/xslt" element={<XSLTGenerator />} />
                  <Route path="/chat" element={<ChatAssistant />} />
                  <Route path="/docs" element={<DocumentGenerator />} />
                  <Route path="/cpi" element={<CPIConnect />} />
                  <Route path="/users" element={<UserManagement />} />
                </Routes>
              </Layout>
            </ProtectedRoute>
          } />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
