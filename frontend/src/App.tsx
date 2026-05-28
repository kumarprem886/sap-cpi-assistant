import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import IFlowGenerator from './pages/IFlowGenerator'
import MessageMapping from './pages/MessageMapping'
import GroovyGenerator from './pages/GroovyGenerator'
import XSLTGenerator from './pages/XSLTGenerator'
import ChatAssistant from './pages/ChatAssistant'
import DocumentGenerator from './pages/DocumentGenerator'
import CPIConnect from './pages/CPIConnect'

export default function App() {
  return (
    <BrowserRouter>
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
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
