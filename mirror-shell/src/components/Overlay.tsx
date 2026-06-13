import { useEffect, useMemo, useState } from 'react'

interface Props {
  clickInfo: { tag?: string; text?: string } | null
  businessJson: { mainActions?: string[] } | null
  pagePurpose?: string
}

const INTERACTIVE_TAGS = ['BUTTON', 'A', 'INPUT', 'SELECT', 'TEXTAREA']

export function Overlay({ clickInfo, businessJson, pagePurpose }: Props) {
  const overlay = useMemo(() => {
    if (!clickInfo) return null

    const isInteractive = INTERACTIVE_TAGS.includes(clickInfo.tag ?? '')
    if (!isInteractive) return null

    const actions: string[] = businessJson?.mainActions ?? []
    const clickText = (clickInfo.text ?? '').toLowerCase()
    const matched = actions.find((a) => a.toLowerCase().includes(clickText))

    const message = matched
      ? matched
      : clickInfo.text
        ? `"${clickInfo.text}" — triggers an action in the live app`
        : `This ${clickInfo.tag?.toLowerCase() ?? 'element'} would trigger an action`

    return { message }
  }, [clickInfo, businessJson])

  const [dismissedClick, setDismissedClick] = useState<Props['clickInfo']>(null)

  useEffect(() => {
    if (!overlay || !clickInfo) return

    const click = clickInfo
    const t = setTimeout(() => setDismissedClick(click), 3500)
    return () => clearTimeout(t)
  }, [clickInfo, overlay])

  if (!overlay || dismissedClick === clickInfo) return null

  return (
    <div className="absolute bottom-6 right-6 z-50 pointer-events-none bg-gray-900 text-white rounded-xl px-4 py-3 shadow-2xl max-w-sm border border-gray-700">
      <p className="text-xs text-yellow-400 font-semibold mb-1">Interactive element</p>
      <p className="text-sm text-gray-200">{overlay.message}</p>
      {pagePurpose && (
        <p className="text-xs text-gray-500 mt-2 line-clamp-2">{pagePurpose}</p>
      )}
    </div>
  )
}
