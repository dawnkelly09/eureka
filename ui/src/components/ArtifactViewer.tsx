import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import styles from './ArtifactViewer.module.css'

interface Props {
  content: string
}

function headingId(children: React.ReactNode): string {
  const text = String(children).replace(/\*\*/g, '').replace(/`/g, '')
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
}

export function ArtifactViewer({ content }: Props) {
  return (
    <article className={styles.viewer}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        children={content}
        components={{
          code({ className, children, ...props }) {
            const isInline = !className
            if (isInline) {
              return <code className={styles.inlineCode} {...props}>{children}</code>
            }
            return (
              <div className={styles.codeBlock}>
                <pre><code className={className} {...props}>{children}</code></pre>
              </div>
            )
          },
          h1: ({ children }) => <h1 id={headingId(children)} className={styles.h1}>{children}</h1>,
          h2: ({ children }) => <h2 id={headingId(children)} className={styles.h2}>{children}</h2>,
          h3: ({ children }) => <h3 id={headingId(children)} className={styles.h3}>{children}</h3>,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer" className={styles.link}>
              {children}
            </a>
          ),
        }}
      />
    </article>
  )
}
