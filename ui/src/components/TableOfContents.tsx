import { useMemo } from 'react'
import styles from './TableOfContents.module.css'

interface TocEntry {
  id: string
  text: string
  level: number
}

interface Props {
  content: string
}

function extractHeadings(markdown: string): TocEntry[] {
  const headings: TocEntry[] = []
  let inCodeBlock = false
  for (const line of markdown.split('\n')) {
    if (line.startsWith('```')) {
      inCodeBlock = !inCodeBlock
      continue
    }
    if (inCodeBlock) continue
    const match = line.match(/^(#{1,3})\s+(.+)/)
    if (match) {
      const text = match[2].replace(/\*\*/g, '').replace(/`/g, '')
      const id = text
        .toLowerCase()
        .replace(/[^a-z0-9\s-]/g, '')
        .replace(/\s+/g, '-')
      headings.push({ id, text, level: match[1].length })
    }
  }
  return headings
}

export function TableOfContents({ content }: Props) {
  const headings = useMemo(() => extractHeadings(content), [content])

  if (headings.length === 0) return null

  function handleClick(id: string) {
    const el = document.getElementById(id)
    if (el) {
      const offset = 120 // header + tab nav height
      const top = el.getBoundingClientRect().top + window.scrollY - offset
      window.scrollTo({ top, behavior: 'smooth' })
    }
  }

  return (
    <nav className={styles.toc}>
      <h2 className={styles.title}>Contents</h2>
      <ul className={styles.list}>
        {headings.map((h, i) => (
          <li key={i} className={styles[`level${h.level}`]}>
            <button className={styles.link} onClick={() => handleClick(h.id)}>
              {h.text}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  )
}
