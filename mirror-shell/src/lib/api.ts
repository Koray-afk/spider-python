const BASE = 'http://localhost:8000'

export async function getCatalog(app: string) {
  const res = await fetch(`${BASE}/apps/${app}/catalog`)
  if (!res.ok) throw new Error(`Catalog not found for ${app}`)
  return res.json()
}

export async function getPageUrl(app: string, pageId: string): Promise<string> {
  const res = await fetch(`${BASE}/apps/${app}/page_url/${pageId}`)
  if (!res.ok) return ''
  const data = await res.json()
  return `${BASE}${data.url}`
}

export async function getBusinessJson(app: string, pageId: string) {
  const res = await fetch(`${BASE}/apps/${app}/business/${pageId}`)
  if (!res.ok) return null
  return res.json()
}

export async function getComponentTree(app: string, pageId: string) {
  const res = await fetch(`${BASE}/apps/${app}/component_tree/${pageId}`)
  if (!res.ok) return null
  return res.json()
}