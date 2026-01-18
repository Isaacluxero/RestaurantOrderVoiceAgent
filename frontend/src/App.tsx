import { useState, useEffect } from 'react'
import './App.css'
import { Call, Menu } from './types'
import CallCard from './components/CallCard'
import Header from './components/Header'
import MenuView from './components/MenuView'
import MetricsView from './components/MetricsView'

type Tab = 'metrics' | 'orders' | 'menu'

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('metrics')
  const [calls, setCalls] = useState<Call[]>([])
  const [menu, setMenu] = useState<Menu | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchOrderHistory = async (suppressError = false) => {
    try {
      setError(null)
      const response = await fetch('/api/orders/history')
      if (!response.ok) {
        throw new Error('Failed to fetch order history')
      }
      const data = await response.json()
      setCalls(data)
    } catch (err) {
      // For metrics view, use empty array instead of showing error
      // This allows metrics to display with zero values
      if (suppressError) {
        setCalls([])
      } else {
        setError(err instanceof Error ? err.message : 'An error occurred')
      }
    }
  }

  const fetchMenu = async (suppressError = false) => {
    try {
      setError(null)
      const response = await fetch('/api/menu')
      if (!response.ok) {
        throw new Error('Failed to fetch menu')
      }
      const data = await response.json()
      setMenu(data)
    } catch (err) {
      // For metrics view, allow it to work without menu (revenue will be 0)
      // Only show error for menu tab
      if (suppressError) {
        setMenu(null)
      } else {
        setError(err instanceof Error ? err.message : 'An error occurred')
      }
    }
  }

  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      // Always suppress errors on initial load - metrics can handle empty data
      await Promise.all([
        fetchOrderHistory(true), 
        fetchMenu(true)
      ])
      setLoading(false)
    }
    loadData()
    
    // Refresh orders every 30 seconds - suppress errors for metrics
    const interval = setInterval(() => {
      fetchOrderHistory(activeTab === 'metrics')
    }, 30000)
    return () => clearInterval(interval)
  }, [activeTab])

  const handleRefresh = () => {
    const isMetrics = activeTab === 'metrics'
    if (activeTab === 'orders' || activeTab === 'metrics') {
      fetchOrderHistory(isMetrics)
    }
    if (activeTab === 'menu' || activeTab === 'metrics') {
      // Metrics needs menu for revenue calculation
      fetchMenu(isMetrics)
    }
  }

  return (
    <div className="app">
      <Header activeTab={activeTab} onTabChange={setActiveTab} onRefresh={handleRefresh} />
      <main className="main-content">
        {loading && (
          <div className="loading">
            <p>Loading...</p>
          </div>
        )}
        {error && (
          <div className="error">
            <p>Error: {error}</p>
            <button onClick={handleRefresh}>Retry</button>
          </div>
        )}
        {!loading && !error && activeTab === 'orders' && calls.length === 0 && (
          <div className="empty">
            <p>No orders found</p>
          </div>
        )}
        {!loading && !error && activeTab === 'orders' && calls.length > 0 && (
          <div className="calls-container">
            {calls.map((call) => (
              <CallCard key={call.id} call={call} />
            ))}
          </div>
        )}
        {!loading && activeTab === 'metrics' && (
          <MetricsView calls={calls} menu={menu} />
        )}
        {!loading && !error && activeTab === 'menu' && menu && (
          <MenuView menu={menu} />
        )}
      </main>
    </div>
  )
}

export default App
