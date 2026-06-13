import { useEffect, useRef } from 'react'

interface Props {
  src: string
  onNavigate: (slug: string) => void
  onElementClick: (info: { tag: string; text: string }) => void
}

function injectMirrorBridge(iframe: HTMLIFrameElement) {
  const doc = iframe.contentDocument
  if (!doc || doc.getElementById('mirror-shell-bridge')) return

  const script = doc.createElement('script')
  script.id = 'mirror-shell-bridge'
  script.textContent = `
    (function() {
      document.addEventListener('click', function(e) {
        var el = e.target;
        if (!el || !el.closest) return;
        var node = el.closest('button, a, input, select, textarea');
        if (!node) return;
        window.parent.postMessage({
          type: 'element_click',
          tag: node.tagName,
          text: (node.textContent || node.value || '').trim().slice(0, 120)
        }, '*');
      }, true);
    })();
  `
  ;(doc.body || doc.documentElement).appendChild(script)
}

function slugFromPath(pathname: string): string | null {
  const match = pathname.match(/\/static\/[^/]+\/([^/]+)\/index\.html/)
  return match?.[1] ?? null
}

export function MirrorCanvas({ src, onNavigate, onElementClick }: Props) {
  const iframeRef = useRef<HTMLIFrameElement>(null)

  useEffect(() => {
    function handleMessage(e: MessageEvent) {
      if (!e.data?.type) return
      if (e.data.type === 'navigate') onNavigate(e.data.slug)
      if (e.data.type === 'element_click') onElementClick(e.data)
    }
    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [onNavigate, onElementClick])

  useEffect(() => {
    const iframe = iframeRef.current
    if (!iframe || !src) return

    function onLoad() {
      injectMirrorBridge(iframe!)
      try {
        const slug = slugFromPath(iframe!.contentWindow?.location.pathname ?? '')
        if (slug) onNavigate(slug)
      } catch {
        // cross-origin guard (should not happen for same-origin static mirror)
      }
    }

    iframe.addEventListener('load', onLoad)
    return () => iframe.removeEventListener('load', onLoad)
  }, [src, onNavigate])

  if (!src) {
    return (
      <div className="w-full h-full flex items-center justify-center text-gray-400 bg-gray-50 text-sm">
        Select a page from the sidebar
      </div>
    )
  }

  return (
    <iframe
      ref={iframeRef}
      src={src}
      className="w-full h-full border-0"
      title="Mirror Canvas"
    />
  )
}
