"""Contenido enriquecido (spec 017): saneamiento de HTML y resolución de imágenes pegadas.

Capa 1 (Core/Dominio) — sin imports de Flask ni SQLAlchemy. `bleach`/`lxml` son librerías de
procesamiento de texto puro, no frameworks de infraestructura (Principio II).
"""
import bleach
from lxml import html as lxml_html

ALLOWED_TAGS = ["p", "br", "strong", "b", "em", "i", "u", "a", "ul", "ol", "li", "img", "blockquote"]
ALLOWED_ATTRIBUTES = {
    "a": ["href", "target", "rel"],
    "img": ["src", "alt"],
}
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def strip_html(html: str) -> str:
    """Despoja todas las etiquetas, dejando solo texto — usado para el chequeo de "vacío"
    (un `<p><br></p>` de un editor de texto enriquecido no es un comentario/descripción vacío
    en apariencia, pero sí lo es en contenido)."""
    if not html:
        return ""
    return bleach.clean(html, tags=[], attributes={}, strip=True)


def sanitize_html(html: str) -> str:
    """Saneamiento autoritativo (server-side, Principio IV) antes de persistir `body`/
    `description`. Lista blanca fija de tags/atributos/protocolos — nunca se confía en el
    saneamiento del cliente."""
    if not html:
        return ""
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES,
                        protocols=ALLOWED_PROTOCOLS, strip=True)


def resolve_pending_images(html: str, id_by_index: dict[int, str], base_url: str) -> str:
    """Reemplaza cada `<img data-pending-id="N">` por su URL real de adjunto ya creado
    (`{base_url}/{attachment_id}`), quitando el atributo temporal. El frontend siempre carga
    estas imágenes vía `apiClient` (autenticado por header JWT) y las muestra como blob URL —
    nunca como `<img src>` nativo, que no podría mandar el header — así que la URL no necesita
    ningún parámetro especial de disposición. Imágenes cuyo índice no tenga un adjunto
    correspondiente (ej. rechazadas por inválidas) se eliminan del HTML en vez de dejar una
    referencia rota."""
    if not html or "data-pending-id" not in html:
        return html
    tree = lxml_html.fromstring(f"<div>{html}</div>")
    for img in tree.xpath("//img[@data-pending-id]"):
        raw_idx = img.get("data-pending-id")
        try:
            idx = int(raw_idx)
        except (TypeError, ValueError):
            idx = None
        attachment_id = id_by_index.get(idx) if idx is not None else None
        if attachment_id:
            img.set("src", f"{base_url}/{attachment_id}")
            del img.attrib["data-pending-id"]
        else:
            img.getparent().remove(img)
    serialized = lxml_html.tostring(tree, encoding="unicode")
    if serialized.startswith("<div>") and serialized.endswith("</div>"):
        serialized = serialized[len("<div>"):-len("</div>")]
    return serialized
