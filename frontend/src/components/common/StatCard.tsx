import type { ReactNode } from 'react'
import { Card, Tag, Tooltip } from 'antd'
import { palette, vivid } from '../../theme'

type StatColor = keyof typeof vivid | 'neutral'

interface StatCardProps {
  label: string
  value: ReactNode
  sub?: string
  icon?: ReactNode
  color?: StatColor
  /** Métrica de una fase futura: se muestra en gris con badge "Próximamente" en vez de un valor real. */
  placeholder?: boolean
  placeholderHint?: string
}

/** Tarjeta de resumen coloreada (Dashboard). Ver docs/PROPUESTA_VISUAL.html. */
export default function StatCard({
  label, value, sub, icon, color = 'neutral', placeholder = false, placeholderHint,
}: StatCardProps) {
  const scheme = color !== 'neutral' ? vivid[color] : { bg: palette.slate50, text: palette.slate700 }
  return (
    <Card
      size="small"
      style={{
        borderRadius: 10,
        borderColor: placeholder ? palette.slate200 : scheme.bg,
        background: placeholder ? palette.slate50 : '#fff',
        opacity: placeholder ? 0.75 : 1,
      }}
      styles={{ body: { padding: '16px 18px' } }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <span style={{ fontSize: 12, fontWeight: 600, letterSpacing: 0.4, textTransform: 'uppercase', color: palette.slate500 }}>
          {label}
        </span>
        {icon && (
          <span style={{
            width: 28, height: 28, borderRadius: 8, display: 'flex', alignItems: 'center',
            justifyContent: 'center', background: scheme.bg, color: scheme.text, fontSize: 15,
          }}>
            {icon}
          </span>
        )}
      </div>
      {placeholder ? (
        <Tooltip title={placeholderHint ?? 'Disponible en una fase futura'}>
          <Tag color="default" style={{ fontSize: 12 }}>Próximamente</Tag>
        </Tooltip>
      ) : (
        <div style={{ fontSize: 26, fontWeight: 700, color: scheme.text, lineHeight: 1.1 }}>{value}</div>
      )}
      {sub && !placeholder && <div style={{ fontSize: 12, color: palette.slate500, marginTop: 4 }}>{sub}</div>}
    </Card>
  )
}
