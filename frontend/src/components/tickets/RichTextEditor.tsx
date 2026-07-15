import { useEffect, useRef } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Image from '@tiptap/extension-image'
import { Button, Space, Tooltip } from 'antd'
import {
  BoldOutlined, ItalicOutlined, UnderlineOutlined, LinkOutlined,
  UnorderedListOutlined, OrderedListOutlined,
} from '@ant-design/icons'
import DOMPurify from 'dompurify'

/** Un documento TipTap "vacío" serializa como `<p></p>` (o similar), nunca como string vacío —
 * usado para validar antes de enviar, en espejo del chequeo server-side (`strip_html`). */
export function isRichTextEmpty(html: string): boolean {
  if (!html) return true
  const div = document.createElement('div')
  div.innerHTML = html
  return !div.textContent?.trim()
}

/** Convierte un `data:` URI (imagen incrustada al copiar de un correo/webmail) en un File,
 * para tratarlo igual que una imagen pegada directamente desde el portapapeles. */
function dataUriToFile(dataUri: string, index: number): File | null {
  const match = /^data:([^;]+);base64,(.+)$/.exec(dataUri)
  if (!match) return null
  const [, mime, base64] = match
  try {
    const binary = atob(base64)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
    return new File([bytes], `pegada-${index}.${mime.split('/')[1] || 'png'}`, { type: mime })
  } catch {
    return null
  }
}

interface RichTextEditorProps {
  /** Opcional: cuando se usa como hijo de un `Form.Item` de Ant Design, `value`/`onChange` los
   * inyecta el propio Form.Item vía `cloneElement`, así que no hace falta pasarlos a mano. */
  value?: string
  onChange?: (html: string) => void
  placeholder?: string
  /** Habilita pegar/soltar imágenes incrustadas (spec 017, US2). Por defecto false: el texto
   * pegado conserva formato compatible, pero las imágenes se descartan (research.md Decisión 2). */
  allowImages?: boolean
  /** Se llama en orden por cada imagen pendiente (pegada o incrustada en HTML copiado) — el
   * padre acumula los archivos; su posición en ese arreglo es el índice usado en
   * `data-pending-id` dentro del HTML. */
  onPendingImage?: (file: File) => void
}

/** Editor de texto enriquecido (spec 017): negrilla, cursiva, subrayado, listas, hipervínculos,
 * y opcionalmente imágenes pegadas/incrustadas. El HTML pegado se sanea con DOMPurify antes de
 * insertarse (primera línea de defensa — el saneamiento autoritativo es server-side, bleach). */
export default function RichTextEditor({ value = '', onChange, placeholder, allowImages = false, onPendingImage }: RichTextEditorProps) {
  const pendingIndexRef = useRef(0)
  const allowImagesRef = useRef(allowImages)
  const onPendingImageRef = useRef(onPendingImage)
  allowImagesRef.current = allowImages
  onPendingImageRef.current = onPendingImage

  const registerPendingImage = (file: File): number => {
    const index = pendingIndexRef.current
    pendingIndexRef.current += 1
    onPendingImageRef.current?.(file)
    return index
  }

  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit,
      Image.configure({ inline: false }),
    ],
    content: value,
    editorProps: {
      attributes: { class: 'sywork-rich-editor-content' },
      transformPastedHTML(html: string) {
        const clean = DOMPurify.sanitize(html, { ADD_ATTR: ['data-pending-id'] })
        if (!allowImagesRef.current) {
          const div = document.createElement('div')
          div.innerHTML = clean
          div.querySelectorAll('img').forEach(img => img.remove())
          return div.innerHTML
        }
        const div = document.createElement('div')
        div.innerHTML = clean
        div.querySelectorAll('img').forEach(img => {
          const src = img.getAttribute('src') || ''
          if (src.startsWith('data:')) {
            const index = pendingIndexRef.current
            const file = dataUriToFile(src, index)
            if (file) {
              registerPendingImage(file)
              img.setAttribute('src', src) // preview inmediata con el propio data URI
              img.setAttribute('data-pending-id', String(index))
            } else {
              img.remove()
            }
          } else if (!src.startsWith('http://') && !src.startsWith('https://')) {
            // ej. cid:... de un correo — no se puede resolver del lado del cliente
            img.remove()
          }
        })
        return div.innerHTML
      },
      handlePaste(_view, event) {
        if (!allowImagesRef.current) return false
        const files = Array.from(event.clipboardData?.files || [])
          .filter(f => f.type.startsWith('image/'))
        if (files.length === 0) return false
        event.preventDefault()
        files.forEach(file => {
          const index = registerPendingImage(file)
          const url = URL.createObjectURL(file)
          editor?.chain().focus().insertContent(
            `<img src="${url}" data-pending-id="${index}">`,
          ).run()
        })
        return true
      },
      handleDrop(_view, event) {
        if (!allowImagesRef.current) return false
        const files = Array.from(event.dataTransfer?.files || [])
          .filter(f => f.type.startsWith('image/'))
        if (files.length === 0) return false
        event.preventDefault()
        files.forEach(file => {
          const index = registerPendingImage(file)
          const url = URL.createObjectURL(file)
          editor?.chain().focus().insertContent(
            `<img src="${url}" data-pending-id="${index}">`,
          ).run()
        })
        return true
      },
    },
    onUpdate: ({ editor: e }) => onChange?.(e.getHTML()),
  })

  useEffect(() => {
    if (editor && value !== editor.getHTML() && value === '') {
      editor.commands.clearContent()
    }
  }, [value, editor])

  if (!editor) return null

  const showPlaceholder = editor.isEmpty && !!placeholder

  const setLink = () => {
    const previous = editor.getAttributes('link').href as string | undefined
    // eslint-disable-next-line no-alert
    const url = window.prompt('URL del hipervínculo', previous || 'https://')
    if (url === null) return
    if (url === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run()
      return
    }
    editor.chain().focus().extendMarkRange('link').setLink({ href: url, target: '_blank' }).run()
  }

  return (
    <div style={{ border: '1px solid #d9d9d9', borderRadius: 6 }}>
      <Space size={2} style={{ padding: '4px 6px', borderBottom: '1px solid #f0f0f0' }} wrap>
        <Tooltip title="Negrilla">
          <Button size="small" type={editor.isActive('bold') ? 'primary' : 'text'}
            icon={<BoldOutlined />} onClick={() => editor.chain().focus().toggleBold().run()} />
        </Tooltip>
        <Tooltip title="Cursiva">
          <Button size="small" type={editor.isActive('italic') ? 'primary' : 'text'}
            icon={<ItalicOutlined />} onClick={() => editor.chain().focus().toggleItalic().run()} />
        </Tooltip>
        <Tooltip title="Subrayado">
          <Button size="small" type={editor.isActive('underline') ? 'primary' : 'text'}
            icon={<UnderlineOutlined />} onClick={() => editor.chain().focus().toggleUnderline().run()} />
        </Tooltip>
        <Tooltip title="Lista con viñetas">
          <Button size="small" type={editor.isActive('bulletList') ? 'primary' : 'text'}
            icon={<UnorderedListOutlined />} onClick={() => editor.chain().focus().toggleBulletList().run()} />
        </Tooltip>
        <Tooltip title="Lista numerada">
          <Button size="small" type={editor.isActive('orderedList') ? 'primary' : 'text'}
            icon={<OrderedListOutlined />} onClick={() => editor.chain().focus().toggleOrderedList().run()} />
        </Tooltip>
        <Tooltip title="Hipervínculo">
          <Button size="small" type={editor.isActive('link') ? 'primary' : 'text'}
            icon={<LinkOutlined />} onClick={setLink} />
        </Tooltip>
      </Space>
      <div style={{ position: 'relative' }}>
        {showPlaceholder && (
          <span style={{
            position: 'absolute', top: 8, left: 12, color: '#bfbfbf', pointerEvents: 'none',
          }}>
            {placeholder}
          </span>
        )}
        <EditorContent editor={editor} />
      </div>
    </div>
  )
}
