import { palette } from '../../theme'

const BANNER_WIDTH = 28

const ENV_CONFIG: Record<string, { label: string; color: string }> = {
  development: { label: 'DESARROLLO', color: palette.slate500 },
  test: { label: 'TEST', color: palette.amber600 },
  production: { label: 'PRODUCCIÓN', color: palette.red600 },
}

/** Identifica visualmente el ambiente (Desarrollo/Test/Producción) en toda la app — spec 027. */
export default function EnvironmentBanner() {
  const env = import.meta.env.VITE_APP_ENV ?? 'development'
  const config = ENV_CONFIG[env] ?? ENV_CONFIG.development

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        bottom: 0,
        width: BANNER_WIDTH,
        background: config.color,
        zIndex: 2000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        boxShadow: '-1px 0 4px rgba(0,0,0,0.15)',
        pointerEvents: 'none',
      }}
    >
      <span
        style={{
          writingMode: 'vertical-rl',
          transform: 'rotate(180deg)',
          color: '#fff',
          fontWeight: 700,
          fontSize: 13,
          letterSpacing: 2,
          whiteSpace: 'nowrap',
        }}
      >
        {config.label}
      </span>
    </div>
  )
}

export { BANNER_WIDTH }
