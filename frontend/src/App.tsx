import { ConfigProvider, Layout, Typography, Tag, Space } from 'antd'
import { CheckCircleOutlined } from '@ant-design/icons'

const { Header, Content } = Layout
const { Title, Text } = Typography

export default function App() {
  return (
    <ConfigProvider theme={{ token: { colorPrimary: '#1677ff' } }}>
      <Layout style={{ minHeight: '100vh' }}>
        <Header style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Title level={4} style={{ color: '#fff', margin: 0 }}>
            SYWork Tickets
          </Title>
          <Tag color="green">v0.1.0</Tag>
        </Header>
        <Content style={{ padding: 40 }}>
          <Space direction="vertical" size="large">
            <Title level={2}>Stack inicializado correctamente</Title>
            <Space>
              <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 18 }} />
              <Text>React + TypeScript strict</Text>
            </Space>
            <Space>
              <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 18 }} />
              <Text>Ant Design</Text>
            </Space>
            <Space>
              <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 18 }} />
              <Text>Zustand · date-fns · @hello-pangea/dnd</Text>
            </Space>
            <Space>
              <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 18 }} />
              <Text>Vite · pnpm</Text>
            </Space>
          </Space>
        </Content>
      </Layout>
    </ConfigProvider>
  )
}
