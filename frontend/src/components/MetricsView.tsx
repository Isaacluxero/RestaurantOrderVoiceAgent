import { Call, Menu } from '../types'
import './MetricsView.css'

interface MetricsViewProps {
  calls: Call[]
  menu: Menu | null
}

interface Metrics {
  totalCalls: number
  completedCalls: number
  failedCalls: number
  inProgressCalls: number
  totalOrders: number
  totalItems: number
  successRate: number
  avgItemsPerOrder: number
  estimatedRevenue: number
  popularItems: Array<{ name: string; count: number; percentage: number }>
  itemsByCategory: Record<string, number>
  recentActivity: Call[]
}

function MetricsView({ calls, menu }: MetricsViewProps) {
  // Calculate metrics from calls data
  const calculateMetrics = (): Metrics => {
    const totalCalls = calls.length
    const completedCalls = calls.filter(c => c.status.toLowerCase() === 'completed').length
    const failedCalls = calls.filter(c => c.status.toLowerCase() === 'failed').length
    const inProgressCalls = calls.filter(c => c.status.toLowerCase() === 'in_progress').length
    
    const totalOrders = calls.reduce((sum, call) => sum + call.orders.length, 0)
    const allOrders = calls.flatMap(call => call.orders)
    const totalItems = allOrders.reduce((sum, order) => sum + order.items.reduce((itemSum, item) => itemSum + item.quantity, 0), 0)
    
    const successRate = totalCalls > 0 ? (completedCalls / totalCalls) * 100 : 0
    const avgItemsPerOrder = totalOrders > 0 ? totalItems / totalOrders : 0
    
    // Calculate estimated revenue from menu prices
    let estimatedRevenue = 0
    if (menu) {
      const itemPrices: Record<string, number> = {}
      menu.items.forEach(item => {
        if (item.price !== null) {
          itemPrices[item.name.toLowerCase()] = item.price
        }
      })
      
      allOrders.forEach(order => {
        order.items.forEach(item => {
          const price = itemPrices[item.item_name.toLowerCase()] || 0
          estimatedRevenue += price * item.quantity
        })
      })
    }
    
    // Calculate popular items
    const itemCounts: Record<string, number> = {}
    allOrders.forEach(order => {
      order.items.forEach(item => {
        const key = item.item_name.toLowerCase()
        itemCounts[key] = (itemCounts[key] || 0) + item.quantity
      })
    })
    
    const popularItems = Object.entries(itemCounts)
      .map(([name, count]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        count,
        percentage: totalItems > 0 ? (count / totalItems) * 100 : 0
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10)
    
    // Calculate items by category
    const itemsByCategory: Record<string, number> = {}
    if (menu) {
      allOrders.forEach(order => {
        order.items.forEach(item => {
          const menuItem = menu.items.find(mi => mi.name.toLowerCase() === item.item_name.toLowerCase())
          if (menuItem && menuItem.category) {
            const category = menuItem.category
            itemsByCategory[category] = (itemsByCategory[category] || 0) + item.quantity
          }
        })
      })
    }
    
    // Recent activity (last 10 calls)
    const recentActivity = [...calls]
      .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())
      .slice(0, 10)
    
    return {
      totalCalls,
      completedCalls,
      failedCalls,
      inProgressCalls,
      totalOrders,
      totalItems,
      successRate,
      avgItemsPerOrder,
      estimatedRevenue,
      popularItems,
      itemsByCategory,
      recentActivity
    }
  }

  const metrics = calculateMetrics()

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount)
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return '#10b981'
      case 'in_progress':
        return '#f59e0b'
      case 'failed':
        return '#ef4444'
      default:
        return '#666'
    }
  }

  return (
    <div className="metrics-view">
      {/* Key Metrics Cards */}
      <div className="metrics-cards">
        <div className="metric-card">
          <div className="metric-icon">📞</div>
          <div className="metric-content">
            <div className="metric-value">{metrics.totalCalls}</div>
            <div className="metric-label">Total Calls</div>
            <div className="metric-details">
              {metrics.completedCalls} completed • {metrics.failedCalls} failed
              {metrics.inProgressCalls > 0 && ` • ${metrics.inProgressCalls} in progress`}
            </div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon">✅</div>
          <div className="metric-content">
            <div className="metric-value">{metrics.totalOrders}</div>
            <div className="metric-label">Total Orders</div>
            <div className="metric-details">
              {metrics.totalItems} items • {metrics.avgItemsPerOrder.toFixed(1)} avg/order
            </div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon">📈</div>
          <div className="metric-content">
            <div className="metric-value">{metrics.successRate.toFixed(1)}%</div>
            <div className="metric-label">Success Rate</div>
            <div className="metric-details">
              {metrics.completedCalls} of {metrics.totalCalls} calls successful
            </div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon">💰</div>
          <div className="metric-content">
            <div className="metric-value">{formatCurrency(metrics.estimatedRevenue)}</div>
            <div className="metric-label">Est. Revenue</div>
            <div className="metric-details">
              From {metrics.totalOrders} confirmed orders
            </div>
          </div>
        </div>
      </div>

      {/* Top Menu Items */}
      {metrics.popularItems.length > 0 && (
        <div className="metrics-section">
          <h2 className="section-title">Top Menu Items</h2>
          <div className="popular-items">
            {metrics.popularItems.map((item, idx) => (
              <div key={item.name} className="popular-item">
                <div className="popular-item-rank">#{idx + 1}</div>
                <div className="popular-item-content">
                  <div className="popular-item-header">
                    <span className="popular-item-name">{item.name}</span>
                    <span className="popular-item-count">{item.count} ordered</span>
                  </div>
                  <div className="popular-item-bar">
                    <div
                      className="popular-item-bar-fill"
                      style={{ width: `${item.percentage}%` }}
                    />
                  </div>
                  <div className="popular-item-percentage">{item.percentage.toFixed(1)}%</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Items by Category */}
      {Object.keys(metrics.itemsByCategory).length > 0 && (
        <div className="metrics-section">
          <h2 className="section-title">Items by Category</h2>
          <div className="category-stats">
            {Object.entries(metrics.itemsByCategory)
              .sort(([, a], [, b]) => b - a)
              .map(([category, count]) => (
                <div key={category} className="category-stat">
                  <span className="category-name">{category.charAt(0).toUpperCase() + category.slice(1)}</span>
                  <span className="category-count">{count} items</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Recent Activity */}
      {metrics.recentActivity.length > 0 && (
        <div className="metrics-section">
          <h2 className="section-title">Recent Activity</h2>
          <div className="recent-activity">
            {metrics.recentActivity.map((call) => {
              const duration = call.ended_at
                ? Math.round((new Date(call.ended_at).getTime() - new Date(call.started_at).getTime()) / 1000)
                : null
              
              return (
                <div key={call.id} className="activity-item">
                  <div className="activity-status" style={{ backgroundColor: getStatusColor(call.status) }} />
                  <div className="activity-content">
                    <div className="activity-header">
                      <span className="activity-call-id">Call {call.id}</span>
                      <span className="activity-status-badge" style={{ color: getStatusColor(call.status) }}>
                        {call.status.replace('_', ' ').toUpperCase()}
                      </span>
                    </div>
                    <div className="activity-details">
                      <span className="activity-time">{formatDate(call.started_at)}</span>
                      {duration && (
                        <span className="activity-duration">
                          {Math.floor(duration / 60)}m {duration % 60}s
                        </span>
                      )}
                      {call.orders.length > 0 && (
                        <span className="activity-orders">{call.orders.length} order(s)</span>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {calls.length === 0 && (
        <div className="metrics-empty">
          <p>No data available yet. Metrics will appear after calls are received.</p>
        </div>
      )}
    </div>
  )
}

export default MetricsView
