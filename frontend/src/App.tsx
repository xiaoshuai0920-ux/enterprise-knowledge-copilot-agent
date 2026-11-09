import { Layout, Menu, Select, Space, Tag } from 'antd'
import { BookOutlined, DashboardOutlined, ExperimentOutlined, MessageOutlined, SafetyOutlined, BugOutlined, ApartmentOutlined } from '@ant-design/icons'
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import DashboardPage from './pages/DashboardPage'
import ChatPage from './pages/ChatPage'
import DocumentsPage from './pages/DocumentsPage'
import TracePage from './pages/TracePage'
import EvaluationPage from './pages/EvaluationPage'
import BadCasesPage from './pages/BadCasesPage'
import PermissionPage from './pages/PermissionPage'
import { identities, useIdentityStore } from './store/identity'

const { Sider, Header, Content } = Layout

export default function App() {
  const location = useLocation(); const navigate = useNavigate()
  const { identity, setIdentity } = useIdentityStore()
  const items = [
    { key: '/dashboard', icon: <DashboardOutlined />, label: '运行总览' },
    { key: '/chat', icon: <MessageOutlined />, label: 'Knowledge Chat' },
    { key: '/documents', icon: <BookOutlined />, label: 'Document Center' },
    { key: '/trace', icon: <ApartmentOutlined />, label: 'RAG Trace' },
    { key: '/evaluation', icon: <ExperimentOutlined />, label: 'Evaluation' },
    { key: '/bad-cases', icon: <BugOutlined />, label: 'Bad Case' },
    { key: '/permissions', icon: <SafetyOutlined />, label: 'Permission Center' }
  ]
  return <Layout style={{ minHeight: '100vh' }}>
    <Sider width={230} theme="dark">
      <div className="app-logo">Knowledge Copilot</div>
      <Menu theme="dark" mode="inline" selectedKeys={[location.pathname]} items={items} onClick={({key}) => navigate(key)} />
    </Sider>
    <Layout>
      <Header style={{ background:'#fff', padding:'0 24px', display:'flex', alignItems:'center', justifyContent:'space-between', borderBottom:'1px solid #edf0f5' }}>
        <Space><b>Enterprise Knowledge Copilot</b><Tag color="blue">Hybrid RAG</Tag><Tag color="purple">ACL</Tag></Space>
        <Space>
          <span className="muted">模拟身份</span>
          <Select value={identity.name} style={{width:150}} options={identities.map(x=>({label:x.name,value:x.name}))} onChange={(v)=>setIdentity(identities.find(x=>x.name===v)!)} />
        </Space>
      </Header>
      <Content><Routes>
        <Route path="/dashboard" element={<DashboardPage/>}/><Route path="/chat" element={<ChatPage/>}/><Route path="/documents" element={<DocumentsPage/>}/>
        <Route path="/trace" element={<TracePage/>}/><Route path="/evaluation" element={<EvaluationPage/>}/><Route path="/bad-cases" element={<BadCasesPage/>}/><Route path="/permissions" element={<PermissionPage/>}/>
        <Route path="*" element={<Navigate to="/dashboard" replace/>}/>
      </Routes></Content>
    </Layout>
  </Layout>
}
