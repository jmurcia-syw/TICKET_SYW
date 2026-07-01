import type { ReactNode } from 'react'
import { Space } from 'antd'

export default function PageToolbar({ filters, action }: { filters: ReactNode; action?: ReactNode }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, gap: 8 }}>
      <Space>{filters}</Space>
      {action}
    </div>
  )
}
