import { Call } from '../types'
import OrderCard from './OrderCard'
import './CallCard.css'

interface CallCardProps {
  call: Call
}

function CallCard({ call }: CallCardProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getStatusBadgeClass = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'status-badge status-completed'
      case 'in_progress':
        return 'status-badge status-in-progress'
      case 'failed':
        return 'status-badge status-failed'
      default:
        return 'status-badge'
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'COMPLETED'
      case 'in_progress':
        return 'IN PROGRESS'
      case 'failed':
        return 'FAILED'
      default:
        return status.replace('_', ' ').toUpperCase()
    }
  }

  const isFailed = call.status.toLowerCase() === 'failed'

  const duration = call.ended_at
    ? Math.round((new Date(call.ended_at).getTime() - new Date(call.started_at).getTime()) / 1000)
    : null

  return (
    <div className={`call-card ${isFailed ? 'call-failed' : ''}`}>
      <div className="call-header">
        <div className="call-info">
          <h2>Call {call.id}</h2>
          <p className="call-sid">{call.call_sid}</p>
          <p className="call-time">
            {formatDate(call.started_at)}
            {duration && <span className="duration"> ({Math.floor(duration / 60)}m {duration % 60}s)</span>}
          </p>
        </div>
        <span className={getStatusBadgeClass(call.status)}>
          {getStatusLabel(call.status)}
        </span>
      </div>

      {isFailed && (
        <div className="call-failed-message">
          <p>⚠️ This call ended in a failed state. No orders were placed.</p>
        </div>
      )}
      
      {call.transcript && (
        <div className="transcript">
          <h3>Transcript</h3>
          <p>{call.transcript}</p>
        </div>
      )}

      {call.orders.length > 0 && (
        <div className="orders-section">
          <h3>Orders ({call.orders.length})</h3>
          <div className="orders-list">
            {call.orders.map((order) => (
              <OrderCard key={order.id} order={order} />
            ))}
          </div>
        </div>
      )}

      {call.orders.length === 0 && (
        <div className="no-orders">
          <p>No orders from this call</p>
        </div>
      )}
    </div>
  )
}

export default CallCard

