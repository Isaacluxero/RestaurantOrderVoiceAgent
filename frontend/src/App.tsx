import { useState, useEffect } from 'react'
import './App.css'
import { Call, Menu } from './types'
import CallCard from './components/CallCard'
import Header from './components/Header'
import MenuView from './components/MenuView'

type Tab = 'orders' | 'menu'

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('orders')
  const [calls, setCalls] = useState<Call[]>([])
  const [menu, setMenu] = useState<Menu | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchOrderHistory = async () => {
    try {
      setError(null)
      const response = await fetch('/api/orders/history')
      if (!response.ok) {
        throw new Error('Failed to fetch order history')
      }
      const data = await response.json()
      setCalls(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    }
  }

  const fetchMenu = async () => {
    try {
      setError(null)
      const response = await fetch('/api/menu')
      if (!response.ok) {
        throw new Error('Failed to fetch menu')
      }
      const data = await response.json()
      setMenu(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    }
  }

  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      await Promise.all([fetchOrderHistory(), fetchMenu()])
      setLoading(false)
    }
    loadData()
    
    // Refresh orders every 30 seconds
    const interval = setInterval(fetchOrderHistory, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleRefresh = () => {
    if (activeTab === 'orders') {
      fetchOrderHistory()
    } else {
      fetchMenu()
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
        {!loading && !error && activeTab === 'menu' && menu && (
          <MenuView menu={menu} />
        )}
      </main>
    </div>
  )
}

export default App
