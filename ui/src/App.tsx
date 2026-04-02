import { useState } from 'react'
import repoData from './data/repos.json'
import { RepoSelector } from './components/RepoSelector'
import { TabNav } from './components/TabNav'
import { ArtifactViewer } from './components/ArtifactViewer'
import { FileActions } from './components/FileActions'
import { TableOfContents } from './components/TableOfContents'
import styles from './App.module.css'

type RepoKey = keyof typeof repoData
type TabKey = 'architecture' | 'claude_md' | 'hooks' | 'skills'

const TAB_LABELS: Record<TabKey, string> = {
  architecture: 'Architecture',
  claude_md: 'CLAUDE.md',
  hooks: 'Hooks',
  skills: 'Skills',
}

function App() {
  const [selectedRepo, setSelectedRepo] = useState<RepoKey>('fastapi')
  const [activeTab, setActiveTab] = useState<TabKey>('architecture')

  const repo = repoData[selectedRepo]
  const content = repo[activeTab]

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.wordmark}>eureka</h1>
          <span className={styles.tagline}>AI-first onboarding</span>
        </div>
        <RepoSelector
          repos={Object.entries(repoData).map(([key, val]) => ({
            key,
            name: val.repo_name,
            url: val.repo_url,
          }))}
          selected={selectedRepo}
          onSelect={(key) => setSelectedRepo(key as RepoKey)}
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
            <FileActions content={content} filename="CLAUDE.md" />
          )}
          {activeTab === 'hooks' && (
            <FileActions content={content} filename="settings.json" />
          )}
          <ArtifactViewer content={content} />
        </main>
      </div>
    </div>
  )
}

export default App
