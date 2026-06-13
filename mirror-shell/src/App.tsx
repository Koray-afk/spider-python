import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { MirrorCanvas } from './components/MirrorCanvas'
import { Overlay } from './components/Overlay'
import { getCatalog, getPageUrl, getBusinessJson } from './lib/api'

const APP_NAME = 'zoho'

interface Page {
  id: string
  title: string
  purpose?: string
}

interface Catalog {
  applicationName?: string
  pages?: Page[]
}

interface ClickInfo {
  tag?: string
  text?: string
}

interface BusinessJson {
  mainActions?: string[]
}

export default function App() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [catalog, setCatalog]           = useState<Catalog | null>(null)
  const [currentPage, setCurrentPage]   = useState<Page | null>(null)
  const [pageUrl, setPageUrl]           = useState<string>('')
  const [clickInfo, setClickInfo]       = useState<ClickInfo | null>(null)
  const [businessJson, setBusinessJson] = useState<BusinessJson | null>(null)

  // Load catalog once — respect ?page= param for initial page
  useEffect(() => {
    getCatalog(APP_NAME).then((data: Catalog) => {
      setCatalog(data)
      const paramId = searchParams.get('page')
      const initial =
        (paramId && data.pages?.find((p) => p.id === paramId)) ||
        data.pages?.[0] ||
        null
      if (initial) setCurrentPage(initial)
    }).catch(console.error)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // When page changes — resolve URL + load context
  useEffect(() => {
    if (!currentPage) return
    getPageUrl(APP_NAME, currentPage.id).then(setPageUrl)
    getBusinessJson(APP_NAME, currentPage.id).then(setBusinessJson)
  }, [currentPage])

  function handlePageChange(page: Page) {
    setCurrentPage(page)
    setSearchParams({ page: page.id })
  }

  function handleIframeNavigate(slug: string) {
    const flat = slug.replace(/^app-\d+-/, '')
    const page = catalog?.pages?.find(
      (p: Page) => p.id === flat || p.id === slug || slug.endsWith(`-${p.id}`),
    )
    if (page) handlePageChange(page)
  }

  const pages: Page[] = catalog?.pages ?? []
  const purpose = currentPage?.purpose ?? ''

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-white">
      {/* Top bar */}
      <div className="flex items-center gap-3 px-4 h-10 border-b border-gray-200 bg-white shrink-0">
        {/* Brand */}
        <span className="text-xs font-bold text-blue-500 uppercase tracking-widest select-none">
          Mirror
        </span>

        <div className="w-px h-4 bg-gray-200" />

        {/* Page selector */}
        <select
          className="text-xs border border-gray-200 rounded px-2 py-1 bg-white text-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-400 max-w-[200px]"
          value={currentPage?.id ?? ''}
          onChange={(e) => {
            const page = pages.find((p) => p.id === e.target.value)
            if (page) handlePageChange(page)
          }}
        >
          {pages.map((p) => (
            <option key={p.id} value={p.id}>
              {p.title || p.id}
            </option>
          ))}
        </select>

        {/* Purpose text */}
        {purpose && (
          <span className="text-xs text-gray-400 truncate flex-1 min-w-0">
            {purpose.length > 120 ? `${purpose.slice(0, 120)}…` : purpose}
          </span>
        )}

        {/* Badge */}
        <span className="ml-auto shrink-0 text-xs font-medium bg-blue-50 text-blue-600 border border-blue-200 rounded px-2 py-0.5">
          Track A · Static Replica
        </span>
      </div>

      {/* Mirror + Overlay */}
      <div className="flex-1 relative overflow-hidden">
        <MirrorCanvas
          src={pageUrl}
          onNavigate={handleIframeNavigate}
          onElementClick={setClickInfo}
        />
        <Overlay
          clickInfo={clickInfo}
          businessJson={businessJson}
          pagePurpose={currentPage?.purpose}
        />
      </div>
    </div>
  )
}
