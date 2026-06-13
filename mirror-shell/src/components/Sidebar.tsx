interface Page {
  id: string
  title: string
  purpose?: string
}

interface CatalogModule {
  id: string
  pages: string[]
}

interface Props {
  catalog: {
    applicationName?: string
    pages?: Page[]
    modules?: CatalogModule[]
  } | null
  currentPageId: string | null | undefined
  onNavigate: (page: Page) => void
}

function buildModuleGroups(catalog: NonNullable<Props['catalog']>): [string, Page[]][] {
  const pageById = new Map<string, Page>()
  catalog.pages?.forEach((page) => pageById.set(page.id, page))

  if (catalog.modules?.length) {
    return catalog.modules
      .map((mod) => [
        mod.id,
        mod.pages.map((id) => pageById.get(id)).filter((p): p is Page => Boolean(p)),
      ] as [string, Page[]])
      .filter(([, pages]) => pages.length > 0)
  }

  return [['General', catalog.pages ?? []]]
}

export function Sidebar({ catalog, currentPageId, onNavigate }: Props) {
  if (!catalog) {
    return (
      <div className="w-64 h-full bg-gray-900 text-gray-400 p-4 text-sm">
        Loading...
      </div>
    )
  }

  const groups = buildModuleGroups(catalog)

  return (
    <div className="w-64 h-full bg-gray-900 text-white overflow-y-auto flex flex-col flex-shrink-0">
      <div className="p-4 border-b border-gray-700">
        <h1 className="text-sm font-bold text-blue-400 uppercase tracking-wider">
          Mirror
        </h1>
        <p className="text-xs text-gray-400 mt-1">
          {catalog.applicationName || 'App replica'}
        </p>
      </div>

      <div className="flex-1 overflow-y-auto py-2">
        {groups.map(([module, pages]) => (
          <div key={module} className="mb-4">
            <div className="px-4 py-1 text-xs text-gray-500 uppercase tracking-wider font-semibold">
              {module}
            </div>
            {pages.map((page) => (
              <button
                key={page.id}
                onClick={() => onNavigate(page)}
                className={`w-full text-left px-4 py-2 text-sm transition-colors hover:bg-gray-700 ${
                  currentPageId === page.id
                    ? 'bg-gray-700 border-l-2 border-blue-400 text-white'
                    : 'text-gray-300 border-l-2 border-transparent'
                }`}
              >
                {page.title || page.id}
              </button>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
