import './Header.css'

type Tab = 'metrics' | 'orders' | 'menu'

interface HeaderProps {
  activeTab: Tab;
  onTabChange: (tab: Tab) => void;
  onRefresh: () => void;
  onLogout: () => void;
}

function Header({ activeTab, onTabChange, onRefresh, onLogout }: HeaderProps) {
  return (
    <header className="header">
      <div className="header-content">
        <div className="header-title-section">
          <h1>Voice Agent Dashboard</h1>
          <p className="phone-number">📞 (978) 997-2543</p>
        </div>
        <div className="header-actions">
          <div className="tabs">
            <button
              className={`tab-button ${activeTab === 'metrics' ? 'active' : ''}`}
              onClick={() => onTabChange('metrics')}
            >
              Metrics
            </button>
            <button
              className={`tab-button ${activeTab === 'orders' ? 'active' : ''}`}
              onClick={() => onTabChange('orders')}
            >
              Order History
            </button>
            <button
              className={`tab-button ${activeTab === 'menu' ? 'active' : ''}`}
              onClick={() => onTabChange('menu')}
            >
              Menu
            </button>
          </div>
          <button onClick={onRefresh} className="refresh-button">
            🔄 Refresh
          </button>
          <button onClick={onLogout} className="logout-button">
            🚪 Logout
          </button>
        </div>
      </div>
    </header>
  )
}

export default Header
