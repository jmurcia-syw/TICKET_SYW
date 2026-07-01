import type { ThemeConfig } from 'antd'

// Sala de control: grafito/pizarra neutro + un acento teal operativo.
// Un solo hue de acento (teal) para acción/estado activo; el resto es estructura neutra.
export const palette = {
  slate50: '#F8FAFC',
  slate100: '#F1F5F9',
  slate200: '#E2E8F0',
  slate300: '#CBD5E1',
  slate400: '#94A3B8',
  slate500: '#64748B',
  slate600: '#475569',
  slate700: '#334155',
  slate800: '#1E293B',
  slate900: '#0F172A',
  teal50: '#E6F5F3',
  teal500: '#14B8A6',
  teal600: '#0D9488',
  teal700: '#0F766E',
  green600: '#16A34A',
  amber600: '#D97706',
  red600: '#DC2626',
}

export const STATUS_COLORS = {
  active: palette.green600,
  inactive: palette.slate400,
}

export const ROLE_COLORS: Record<'admin' | 'coordinator' | 'qm' | 'resolver', string> = {
  admin: palette.slate800,
  coordinator: palette.teal600,
  qm: palette.amber600,
  resolver: palette.slate500,
}

export const theme: ThemeConfig = {
  token: {
    colorPrimary: palette.teal600,
    colorLink: palette.teal600,
    colorSuccess: palette.green600,
    colorWarning: palette.amber600,
    colorError: palette.red600,
    colorBgLayout: palette.slate50,
    colorBorderSecondary: palette.slate200,
    colorTextSecondary: palette.slate600,
    colorTextTertiary: palette.slate500,
    borderRadius: 6,
    borderRadiusLG: 8,
    fontFamily:
      "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif",
  },
  components: {
    Layout: {
      headerBg: palette.slate900,
      siderBg: palette.slate50,
      bodyBg: palette.slate50,
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: palette.teal50,
      itemSelectedColor: palette.teal700,
      itemHoverBg: palette.slate100,
    },
    Table: {
      headerBg: palette.slate100,
      headerColor: palette.slate700,
      borderColor: palette.slate200,
    },
  },
}
