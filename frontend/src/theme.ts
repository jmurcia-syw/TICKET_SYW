import type { ThemeConfig } from 'antd'

// Sala de control: grafito/pizarra neutro + acento terracota (naranja apagado,
// estilo Claude) en la UI (botones, links, menú). El logo y
// `brandRed*`/`brandCharcoal` (extraídos de docs/iconoSW.jpg: S roja #EB3037,
// W carbón #353336) se mantienen intactos — siguen usándose en
// ROLE_COLOR_PALETTE y quedan disponibles para acentos puntuales cerca del
// logo. El acento teal queda como respaldo, hoy solo usado por
// CALENDAR_CATEGORY_COLORS.oficial (spec 021).
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
  amber100: '#FEF3C7',
  amber600: '#D97706',
  amber800: '#92400E',
  red600: '#DC2626',
  blue200: '#BFDBFE',
  blue900: '#1E3A8A',
  // Marca SyWork (docs/iconoSW.jpg) — logo y ROLE_COLOR_PALETTE
  brandRed50: '#FDECEC',
  brandRed500: '#EB3037',
  brandRed600: '#D42229',
  brandRed700: '#B01B21',
  brandCharcoal: '#353336',
  // Acento terracota de la UI (botones, links, menú) — apagado a propósito
  // para no chocar con los naranjas vivos ya usados (prioridad "Alta",
  // chip de estado "En Ejecución", colorWarning ámbar).
  brandOrange50: '#FBEDE7',
  brandOrange500: '#D97757',
  brandOrange600: '#B85C3E',
  violet500: '#9254DE',
  lime600: '#7CB305',
}

// Categorías del calendario de festivos/cumpleaños (spec 021) — colores elegidos para no
// repetir ningún hex de PRIORITY_CHIP/TICKET_STATUS_CHIP/STATUS_COLORS, que ya agotan
// naranja/verde/púrpura vivos como semántica de tickets.
export const CALENDAR_CATEGORY_COLORS = {
  oficial: palette.teal700,
  regional_religioso: palette.violet500,
  cumpleanos: palette.lime600,
}

export const STATUS_COLORS = {
  active: palette.green600,
  inactive: palette.slate400,
}

// Paleta viva para Tickets (Dashboard, Triage, Detalle) — chips con fondo suave
// y texto saturado, inspirada en docs/PROPUESTA_VISUAL.html.
export const vivid = {
  blue: { bg: '#E6F4FF', text: '#0958D9' },
  gold: { bg: '#FFF7E6', text: '#D48806' },
  purple: { bg: '#F9F0FF', text: '#531DAB' },
  magenta: { bg: '#FFF0F6', text: '#C41D7F' },
  green: { bg: '#F6FFED', text: '#389E0D' },
  gray: { bg: '#F5F5F5', text: '#595959' },
  red: { bg: '#FFF1F0', text: '#CF1322' },
  cyan: { bg: '#E6FFFB', text: '#08979C' },
  orange: { bg: '#FFF2E8', text: '#D4380D' },
}

/** Chip suave (fondo pastel + texto saturado) por estado del ticket. */
export const TICKET_STATUS_CHIP: Record<string, { bg: string; text: string }> = {
  nuevo: vivid.blue,
  pre_analisis: vivid.cyan,
  contacto: vivid.gold,
  en_analisis: vivid.purple,
  en_ejecucion: vivid.orange,
  en_pruebas: vivid.magenta,
  pendiente_usuario: vivid.red,
  resuelto: vivid.green,
  cerrado: vivid.gray,
  cancelado: vivid.gray,
}

/** Badge sólido por prioridad (fondo saturado + texto blanco/oscuro), estilo p1..p4. */
export const PRIORITY_CHIP: Record<string, { bg: string; text: string }> = {
  critical: { bg: '#FF4D4F', text: '#FFFFFF' },
  high: { bg: '#FA8C16', text: '#FFFFFF' },
  medium: { bg: '#FADB14', text: '#262626' },
  low: { bg: '#D9D9D9', text: '#595959' },
}

/** Paleta de avatares (autores de comentarios, resolutores) — determinística por texto. */
const AVATAR_PALETTE = [
  { bg: '#BAE0FF', text: '#0958D9' },
  { bg: '#D9F7BE', text: '#237804' },
  { bg: '#EFDBFF', text: '#531DAB' },
  { bg: '#FFF1F0', text: '#A8071A' },
  { bg: '#FFE7BA', text: '#AD4E00' },
  { bg: '#FFD6E7', text: '#C41D7F' },
]

export function avatarColor(seed: string | null | undefined): { bg: string; text: string } {
  if (!seed) return AVATAR_PALETTE[0]
  let hash = 0
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) >>> 0
  return AVATAR_PALETTE[hash % AVATAR_PALETTE.length]
}

export function initials(fullName: string | null | undefined): string {
  if (!fullName) return '?'
  const parts = fullName.trim().split(/\s+/)
  return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase() || fullName[0].toUpperCase()
}

const ROLE_COLOR_PALETTE = [palette.slate800, palette.brandRed600, palette.amber600, palette.slate500, palette.green600, palette.brandCharcoal]

/** Asigna un color determinístico a un nombre de rol, sin depender de una lista fija de roles. */
export function roleColor(name: string | null | undefined): string {
  if (!name) return palette.slate400
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = (hash * 31 + name.charCodeAt(i)) >>> 0
  }
  return ROLE_COLOR_PALETTE[hash % ROLE_COLOR_PALETTE.length]
}

export const theme: ThemeConfig = {
  token: {
    colorPrimary: palette.brandOrange500,
    colorLink: palette.brandOrange600,
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
      headerBg: palette.brandCharcoal,
      siderBg: palette.slate50,
      bodyBg: palette.slate50,
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: palette.brandOrange50,
      itemSelectedColor: palette.brandOrange600,
      itemHoverBg: palette.slate100,
    },
    Table: {
      headerBg: palette.slate100,
      headerColor: palette.slate700,
      borderColor: palette.slate200,
    },
  },
}
