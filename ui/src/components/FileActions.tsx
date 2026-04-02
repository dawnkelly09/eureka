import { useState } from 'react'
import styles from './FileActions.module.css'

interface Props {
  content: string
  filename: string
  hint?: string
}

export function FileActions({ content, filename, hint }: Props) {
  const [copied, setCopied] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  function handleDownload() {
    const blob = new Blob([content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.bar}>
        <span className={styles.filename}>{filename}</span>
        <div className={styles.actions}>
          <button className={styles.button} onClick={handleCopy}>
            {copied ? 'Copied' : 'Copy'}
          </button>
          <button className={styles.button} onClick={handleDownload}>
            Download
          </button>
        </div>
      </div>
      {hint && <p className={styles.hint}>{hint}</p>}
    </div>
  )
}
