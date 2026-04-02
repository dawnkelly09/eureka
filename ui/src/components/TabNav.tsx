import styles from './TabNav.module.css'

interface Props {
  tabs: Record<string, string>
  activeTab: string
  onSelect: (tab: string) => void
}

export function TabNav({ tabs, activeTab, onSelect }: Props) {
  return (
    <nav className={styles.nav}>
      <div className={styles.tabs}>
        {Object.entries(tabs).map(([key, label]) => (
          <button
            key={key}
            className={`${styles.tab} ${key === activeTab ? styles.active : ''}`}
            onClick={() => onSelect(key)}
          >
            {label}
          </button>
        ))}
      </div>
    </nav>
  )
}
