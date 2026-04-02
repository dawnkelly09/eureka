import styles from './RepoSelector.module.css'

interface Repo {
  key: string
  name: string
  url: string
}

interface Props {
  repos: Repo[]
  selected: string
  onSelect: (key: string) => void
}

export function RepoSelector({ repos, selected, onSelect }: Props) {
  return (
    <div className={styles.selector}>
      {repos.map((repo) => (
        <button
          key={repo.key}
          className={`${styles.repoButton} ${repo.key === selected ? styles.active : ''}`}
          onClick={() => onSelect(repo.key)}
        >
          <span className={styles.repoName}>{repo.name}</span>
        </button>
      ))}
    </div>
  )
}
