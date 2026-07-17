/** Fase 5 (spec 020): huso horario IANA para Cliente/Recurso. `Intl.supportedValuesOf` es
 * estándar (Baseline 2023, soportado por todos los navegadores del proyecto) — sin dependencia
 * externa (Principio V). El `lib` de TS del proyecto (ES2020) no incluye su tipo todavía, de ahí
 * el cast puntual en vez de ampliar el `lib` global del proyecto. */
type IntlWithSupportedValuesOf = typeof Intl & { supportedValuesOf(key: 'timeZone'): string[] }

export const TIMEZONES: string[] = (() => {
  try {
    return (Intl as IntlWithSupportedValuesOf).supportedValuesOf('timeZone')
  } catch {
    return ['UTC', 'America/Bogota', 'America/Mexico_City', 'America/New_York']
  }
})()
