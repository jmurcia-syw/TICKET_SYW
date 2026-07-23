import type { ReactNode } from 'react'
import { Space } from 'antd'

export default function PageToolbar({ filters, action }: { filters: ReactNode; action?: ReactNode }) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', marginBottom: 16, gap: 8 }}>
      <Space wrap>{filters}</Space>
      {action}
    </div>
  )
}
