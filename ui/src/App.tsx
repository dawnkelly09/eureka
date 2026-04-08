import { useState, useEffect } from 'react'
import { RepoSelector } from './components/RepoSelector'
import { TabNav } from './components/TabNav'
import { ArtifactViewer } from './components/ArtifactViewer'
import { FileActions } from './components/FileActions'
import { TableOfContents } from './components/TableOfContents'
import styles from './App.module.css'

interface RepoData {
  repo_url: string
  repo_name: string
  architecture: string
  claude_md: string
  hooks: string
  skills: string
}

type TabKey = 'architecture' | 'claude_md' | 'hooks' | 'skills'

const TAB_LABELS: Record<TabKey, string> = {
  architecture: 'Architecture',
  claude_md: 'CLAUDE.md',
  hooks: 'Hooks',
  skills: 'Skills',
}

function cleanSkillsContent(raw: string): string {
  return raw
    .split('\n')
    .filter((line) => !line.startsWith('=== skill:'))
    .map((line) => {
      // Demote H1 → H2, H2 → H3
      if (line.startsWith('## ')) return '###' + line.slice(2)
      if (line.startsWith('# ')) return '##' + line.slice(1)
      return line
    })
    .join('\n')
}

function App() {
  const [repos, setRepos] = useState<Record<string, RepoData>>({})
  const [selectedRepo, setSelectedRepo] = useState<string>('')
  const [activeTab, setActiveTab] = useState<TabKey>('architecture')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchRepos = () => {
      fetch('/repos')
        .then((res) => {
          if (!res.ok) throw new Error(`API returned ${res.status}`)
          return res.json()
        })
        .then((data: Record<string, RepoData>) => {
          setRepos(data)
          const keys = Object.keys(data)
          if (keys.length > 0 && !selectedRepo) {
            setSelectedRepo(keys[0])
          }
          setLoading(false)
        })
        .catch((err) => {
          setError(err.message)
          setLoading(false)
        })
    }

    fetchRepos()
    const interval = setInterval(fetchRepos, 5000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className={styles.app}>
        <header className={styles.header}>
          <div className={styles.headerLeft}>
            <h1 className={styles.wordmark}>eureka</h1>
            <span className={styles.tagline}>AI-first onboarding</span>
          </div>
        </header>
        <div className={styles.loading}>Loading repos...</div>
      </div>
    )
  }

  if (error || Object.keys(repos).length === 0) {
    return (
      <div className={styles.app}>
        <header className={styles.header}>
          <div className={styles.headerLeft}>
            <h1 className={styles.wordmark}>eureka</h1>
            <span className={styles.tagline}>AI-first onboarding</span>
          </div>
        </header>
        <div className={styles.loading}>
          {error ? `Error: ${error}` : 'No completed runs yet. POST to /analyze to get started.'}
        </div>
      </div>
    )
  }

  const repo = repos[selectedRepo]
  if (!repo) return null

  const rawContent = repo[activeTab]
  const content = activeTab === 'skills' ? cleanSkillsContent(rawContent) : rawContent

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.wordmark}>eureka</h1>
          <span className={styles.tagline}>AI-first onboarding</span>
        </div>
        <RepoSelector
          repos={Object.entries(repos).map(([key, val]) => ({
            key,
            name: val.repo_name,
            url: val.repo_url,
          }))}
          selected={selectedRepo}
          onSelect={(key) => setSelectedRepo(key)}
        />
      </header>

      <TabNav
        tabs={TAB_LABELS}
        activeTab={activeTab}
        onSelect={(tab) => setActiveTab(tab as TabKey)}
      />

      <div className={styles.layout}>
        <aside className={styles.sidebar}>
          <TableOfContents content={content} />
        </aside>
        <main className={styles.main}>
          {activeTab === 'claude_md' && (
            <FileActions
              content={content}
              filename="CLAUDE.md"
              hint="Drop this file into a Claude Code session and ask it to update the .claude/CLAUDE.md in your repo root to give Claude Code extended context on the codebase."
            />
          )}
          {activeTab === 'hooks' && (
            <FileActions
              content={content}
              filename="settings.json"
              hint="Drop this file into a Claude Code session and ask it to update .claude/settings.json to add these hooks to your environment."
            />
          )}
          {activeTab === 'skills' && (
            <FileActions
              content={rawContent}
              filename="skills.md"
              hint={`Drop this file into a Claude Code session and ask it to install these skills into .claude/skills/${repo.repo_name}/`}
            />
          )}
          <ArtifactViewer content={content} />
        </main>
      </div>
    </div>
  )
}

export default App
