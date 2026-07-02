import { Modal, Typography } from 'antd'
import { ExclamationCircleOutlined } from '@ant-design/icons'
import { palette } from '../../theme'

interface Props {
  open: boolean
  title: string
  description: string
  onConfirm: () => void
  onCancel: () => void
  confirmText?: string
  danger?: boolean
}

export default function ConfirmationModal({ open, title, description, onConfirm, onCancel, confirmText = 'Confirmar', danger = true }: Props) {
  return (
    <Modal
      open={open}
      title={<span><ExclamationCircleOutlined style={{ color: danger ? palette.red600 : palette.amber600, marginRight: 8 }} />{title}</span>}
      okText={confirmText}
      cancelText="Cancelar"
      okButtonProps={{ danger }}
      onOk={onConfirm}
      onCancel={onCancel}
    >
      <Typography.Text>{description}</Typography.Text>
    </Modal>
  )
}
