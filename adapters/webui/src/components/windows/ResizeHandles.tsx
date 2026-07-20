import { cn } from '@/lib/utils'

const MIN_W = 300
const MIN_H = 200

type Dir = 'n' | 'ne' | 'e' | 'se' | 's' | 'sw' | 'w' | 'nw'

const HANDLES: { dir: Dir; className: string }[] = [
  { dir: 'n',  className: 'absolute top-0 left-3 right-3 h-1.5 cursor-n-resize' },
  { dir: 'ne', className: 'absolute top-0 right-0 w-3 h-3 cursor-ne-resize' },
  { dir: 'e',  className: 'absolute top-3 bottom-3 right-0 w-1.5 cursor-e-resize' },
  { dir: 'se', className: 'absolute bottom-0 right-0 w-3 h-3 cursor-se-resize' },
  { dir: 's',  className: 'absolute bottom-0 left-3 right-3 h-1.5 cursor-s-resize' },
  { dir: 'sw', className: 'absolute bottom-0 left-0 w-3 h-3 cursor-sw-resize' },
  { dir: 'w',  className: 'absolute top-3 bottom-3 left-0 w-1.5 cursor-w-resize' },
  { dir: 'nw', className: 'absolute top-0 left-0 w-3 h-3 cursor-nw-resize' },
]

interface ResizeHandlesProps {
  pos: { x: number; y: number }
  size: { width: number; height: number }
  onResize: (pos: { x: number; y: number }, size: { width: number; height: number }) => void
}

export function ResizeHandles({ pos, size, onResize }: ResizeHandlesProps) {
  function startResize(dir: Dir, e: React.PointerEvent) {
    e.preventDefault()
    e.stopPropagation()

    const startX = e.clientX
    const startY = e.clientY
    const orig = { pos: { ...pos }, size: { ...size } }

    const onMove = (ev: PointerEvent) => {
      const dx = ev.clientX - startX
      const dy = ev.clientY - startY

      let newW = orig.size.width
      let newH = orig.size.height
      let newX = orig.pos.x
      let newY = orig.pos.y

      if (dir.includes('e')) newW = Math.max(MIN_W, orig.size.width + dx)
      if (dir.includes('s')) newH = Math.max(MIN_H, orig.size.height + dy)
      if (dir.includes('w')) {
        newW = Math.max(MIN_W, orig.size.width - dx)
        newX = orig.pos.x + orig.size.width - newW
      }
      if (dir.includes('n')) {
        newH = Math.max(MIN_H, orig.size.height - dy)
        newY = orig.pos.y + orig.size.height - newH
      }

      onResize({ x: newX, y: newY }, { width: newW, height: newH })
    }

    const onUp = () => {
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerup', onUp)
    }

    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerup', onUp)
  }

  return (
    <>
      {HANDLES.map(({ dir, className }) => (
        <div
          key={dir}
          className={cn(className, 'z-10')}
          onPointerDown={(e) => startResize(dir, e)}
        />
      ))}
    </>
  )
}
