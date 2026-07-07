import { useCallback, useEffect, useState } from 'react'
import { Button, Card, Col, Form, Input, Row, Table, Tooltip, message } from 'antd'
import { PlusOutlined, StopOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { catalogService } from '../services/catalogService'
import type { CatalogItem, CatalogName } from '../types/catalog'
import { CATALOG_LABELS } from '../types/catalog'
import StatusTag from '../components/common/StatusTag'
import { clientColumnFilter, clientTextColumnFilter } from '../components/common/columnFilters'
import { useAuthStore } from '../store/authStore'
import { palette } from '../theme'

const CATALOGS: CatalogName[] = ['tools', 'processes', 'resolution-types', 'record-types']

function CatalogCard({ catalog }: { catalog: CatalogName }) {
  const { hasPermission } = useAuthStore()
  const canCreate = hasPermission('catalogs', 'create')
  const canDeactivate = hasPermission('catalogs', 'deactivate')
  const [items, setItems] = useState<CatalogItem[]>([])
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm<{ name: string }>()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setItems((await catalogService.list(catalog, 'all')).items)
    } finally {
      setLoading(false)
    }
  }, [catalog])

  useEffect(() => { load() }, [load])

  const apiError = (err: unknown, fallback: string) =>
    (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? fallback

  const handleAdd = async ({ name }: { name: string }) => {
    try {
      await catalogService.create(catalog, name.trim())
      form.resetFields()
      load()
    } catch (err: unknown) {
      message.error(apiError(err, 'Error al agregar el valor'))
    }
  }

  const toggle = async (item: CatalogItem) => {
    try {
      if (item.active) await catalogService.deactivate(catalog, item.id)
      else await catalogService.activate(catalog, item.id)
      load()
    } catch (err: unknown) {
      message.error(apiError(err, 'No se pudo cambiar el estado'))
    }
  }

  return (
    <Card title={CATALOG_LABELS[catalog]} size="small">
      <Table
        rowKey="id" size="small" loading={loading} dataSource={items} pagination={false}
        columns={[
          {
            title: 'Nombre', dataIndex: 'name',
            ...clientTextColumnFilter<CatalogItem>('Buscar nombre...', r => r.name),
          },
          {
            title: 'Estado', dataIndex: 'active', width: 90, render: (v: boolean) => <StatusTag active={v} />,
            ...clientColumnFilter<CatalogItem>(
              [{ text: 'Activo', value: 'true' }, { text: 'Inactivo', value: 'false' }],
              (value, record) => String(record.active) === value,
            ),
          },
          ...(canDeactivate ? [{
            title: '', key: 'toggle', width: 60,
            render: (_: unknown, item: CatalogItem) => (
              <Tooltip title={item.active ? 'Desactivar' : 'Activar'}>
                <Button size="small" danger={item.active}
                  icon={item.active ? <StopOutlined /> : <PlayCircleOutlined style={{ color: palette.green600 }} />}
                  onClick={() => toggle(item)} />
              </Tooltip>
            ),
          }] : []),
        ]}
      />
      {canCreate && (
        <Form form={form} layout="inline" onFinish={handleAdd} style={{ marginTop: 8 }}>
          <Form.Item name="name" rules={[{ required: true, message: 'Nombre requerido' }]}>
            <Input placeholder="Nuevo valor" style={{ width: 180 }} />
          </Form.Item>
          <Form.Item>
            <Button htmlType="submit" icon={<PlusOutlined />}>Agregar</Button>
          </Form.Item>
        </Form>
      )}
    </Card>
  )
}

export default function CatalogsPage() {
  return (
    <Row gutter={[16, 16]}>
      {CATALOGS.map(c => (
        <Col key={c} xs={24} lg={8}>
          <CatalogCard catalog={c} />
        </Col>
      ))}
    </Row>
  )
}
