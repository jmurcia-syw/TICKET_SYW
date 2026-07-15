# UAT — Metodología de Validación Funcional

> **UAT ≠ SDD.** `specs/` y `.specify/` (Spec-Driven Development, Spec Kit) documentan **qué se va a construir, antes de programar**. Esta carpeta `UAT/` documenta **qué se encontró al probar lo ya construido**. Son flujos complementarios, no sustitutos.

## Propósito

Estructurar las pruebas funcionales como especificaciones que Claude Code pueda interpretar directamente — sin pasar por Word ni por reportes narrativos sueltos.

## Roles

| Rol | Responsabilidad en este framework |
|---|---|
| **Validador(es)** — Gerente de Desarrollo y/o consultores asignados a pruebas | Ejecuta pruebas funcionales navegando la app completa (no un módulo aislado). Registra observaciones, adjunta evidencia, define criterios de aceptación. Verifica cierres y acepta Deliveries. **No modifica código.** |
| **Desarrollador (+ Claude Code)** | Lee `ITER-XXX.md` y `BACKLOG.md`, corrige, actualiza estado en `BACKLOG.md`, hace commit y avisa que hay nueva versión para retest. |

> El rol de Validador no está atado a una sola persona: en el futuro pueden participar varios consultores probando en paralelo dentro de la misma iteración. Por eso cada observación registra explícitamente **quién la reportó** (ver `CONVENTIONS.md`), independientemente de quién coordina la iteración o quién firma la aceptación de una Delivery.

## Estructura de carpetas

```
UAT/
├── README.md                    # este archivo
├── CONVENTIONS.md               # nomenclatura, estados, reglas
├── 00_Templates/
│   ├── ITERATION_TEMPLATE.md
│   └── DELIVERY_TEMPLATE.md
├── 01_Iterations/
│   └── ITER-XXX/
│       ├── ITER-XXX.md
│       ├── images/              # capturas, nombradas OBS-XXXX-NN.png
│       └── attachments/         # logs, exports, otros adjuntos
├── 02_Backlog/
│   └── BACKLOG.md               # única fuente de verdad del estado de cada observación
└── 03_Deliveries/
    └── DEL-XXX/
        └── DEL-XXX.md           # acta de aceptación de un corte de versión de la app
```

## Modelo de trabajo

Cada **iteración** es una sesión completa de pruebas: no se prueba un módulo aislado, se navega la aplicación completa y se registra cada hallazgo donde aparezca. Por eso cada observación lleva un campo obligatorio de **módulo/pantalla** y de **reportado por**, que es lo que permite agrupar y rastrear por área o por persona aunque las pruebas no estén organizadas por módulo ni las haga siempre la misma persona.

Una **Delivery** no es 1 a 1 con una iteración: es un corte de versión de la app completa, aceptado formalmente después de acumular las iteraciones necesarias para que el backlog abierto quede en un estado aceptable.

## Flujo de trabajo

### Validador
1. Recibe aviso de nueva versión disponible (fuera de este framework, por chat/correo).
2. `git pull`, levanta el entorno Docker.
3. Navega la aplicación libremente, probando lo que considere necesario.
4. Por cada hallazgo:
   - Revisa `02_Backlog/BACKLOG.md` para ver si ya existe una observación abierta equivalente, o si es la reapertura de una cerrada.
   - Asigna el siguiente `OBS-XXXX` disponible (consecutivo del último registrado en `BACKLOG.md`).
   - Guarda capturas en `01_Iterations/ITER-XXX/images/` con el nombre `OBS-XXXX-NN.png`.
   - Redacta la observación en `ITER-XXX.md` usando `00_Templates/ITERATION_TEMPLATE.md`, indicando quién la reportó.
5. Al cerrar la sesión, agrega/actualiza las filas correspondientes en `BACKLOG.md`.
6. Notifica al desarrollador indicando la ruta del `ITER-XXX.md`.
7. Cuando el estado acumulado de las iteraciones es aceptable, genera una `DEL-XXX.md` con `00_Templates/DELIVERY_TEMPLATE.md` y firma la aceptación.

### Desarrollador
1. Lee el `ITER-XXX.md` más reciente y `BACKLOG.md`.
2. Corrige, priorizando por módulo.
3. Actualiza el estado de cada observación resuelta en `BACKLOG.md` (`En Desarrollo` → `Lista para Validar`).
4. Commit y aviso de que hay nueva versión para retest.

## Guía de interpretación para Claude

- **`BACKLOG.md` es la única fuente de verdad del estado vivo.** No infieras el estado de una observación desde un `ITER-XXX.md` antiguo.
- **Los archivos `ITER-XXX.md` son inmutables** una vez creados: son un registro histórico del punto en el tiempo en que se probó. No se editan retroactivamente.
- **Los IDs (`OBS-`, `ITER-`, `DEL-`) nunca se reutilizan ni se renumeran**, incluso si una observación se rechaza o una iteración queda vacía.
- Antes de crear una observación nueva, busca en `BACKLOG.md` si el mismo síntoma ya tiene un ID abierto para ese módulo.
- Las imágenes referenciadas en una observación deben existir en `images/` de esa misma iteración, con ruta relativa.
- El campo "Reportado por" identifica a la persona, no al rol — no asumir que siempre es la misma persona entre observaciones de una misma iteración.
- Ver `CONVENTIONS.md` para el detalle de nomenclatura, estados y formato exacto de cada campo.
