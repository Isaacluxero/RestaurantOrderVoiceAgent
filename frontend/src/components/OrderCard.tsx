import { Order } from '../types'
import './OrderCard.css'

interface OrderCardProps {
  order: Order
}

function OrderCard({ order }: OrderCardProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  const getStatusBadgeClass = (status: string) => {
    switch (status.toLowerCase()) {
      case 'confirmed':
        return 'order-status-badge status-confirmed'
      case 'pending':
        return 'order-status-badge status-pending'
      case 'cancelled':
        return 'order-status-badge status-cancelled'
      default:
        return 'order-status-badge'
    }
  }

  return (
    <div className="order-card">
      <div className="order-header">
        <div className="order-info">
          <h4>Order #{order.id}</h4>
          <p className="order-time">{formatDate(order.created_at)}</p>
        </div>
        <span className={getStatusBadgeClass(order.status)}>
          {order.status.toUpperCase()}
        </span>
      </div>

      {order.items.length > 0 && (
        <div className="order-items">
          <h5>Items:</h5>
          <ul>
            {order.items.map((item) => (
              <li key={item.id} className="order-item">
                <span className="item-quantity">{item.quantity}x</span>
                <span className="item-name">{item.item_name}</span>
                {item.modifiers && item.modifiers.length > 0 && (
                  <span className="item-modifiers">
                    ({item.modifiers.join(', ')})
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {order.raw_text && (
        <div className="order-raw-text">
          <p><strong>Original text:</strong> {order.raw_text}</p>
        </div>
      )}
    </div>
  )
}

export default OrderCard

