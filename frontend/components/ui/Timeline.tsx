'use client'

import { cn } from '@/lib/utils'
import { 
  CheckCircleIcon, 
  ExclamationTriangleIcon, 
  XCircleIcon, 
  ClockIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline'
import { format } from 'date-fns'

interface TimelineEvent {
  id: string
  type: 'validation' | 'review' | 'update' | 'error'
  title: string
  description?: string
  timestamp: string
  status: 'success' | 'warning' | 'error' | 'pending'
  source?: string
  confidence?: number
  user?: string
  metadata?: Record<string, any>
}

interface TimelineProps {
  events: TimelineEvent[]
  className?: string
  showSource?: boolean
  showConfidence?: boolean
  compact?: boolean
}

export function Timeline({
  events,
  className,
  showSource = true,
  showConfidence = true,
  compact = false,
}: TimelineProps) {
  const sortedEvents = [...events].sort((a, b) => 
    new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  )

  const getStatusIcon = (status: string) => {
    const iconClass = compact ? 'h-4 w-4' : 'h-5 w-5'
    
    switch (status) {
      case 'success':
        return <CheckCircleIcon className={cn(iconClass, 'text-success-500')} />
      case 'warning':
        return <ExclamationTriangleIcon className={cn(iconClass, 'text-warning-500')} />
      case 'error':
        return <XCircleIcon className={cn(iconClass, 'text-error-500')} />
      case 'pending':
        return <ClockIcon className={cn(iconClass, 'text-gray-400')} />
      default:
        return <ArrowPathIcon className={cn(iconClass, 'text-gray-400')} />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'border-success-200 bg-success-50'
      case 'warning':
        return 'border-warning-200 bg-warning-50'
      case 'error':
        return 'border-error-200 bg-error-50'
      case 'pending':
        return 'border-gray-200 bg-gray-50'
      default:
        return 'border-gray-200 bg-white'
    }
  }

  return (
    <div className={cn('flow-root', className)}>
      <ul className="-mb-8">
        {sortedEvents.map((event, eventIdx) => (
          <li key={event.id}>
            <div className="relative pb-8">
              {eventIdx !== sortedEvents.length - 1 && (
                <span
                  className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200"
                  aria-hidden="true"
                />
              )}
              <div className="relative flex space-x-3">
                <div>
                  <span
                    className={cn(
                      'flex h-8 w-8 items-center justify-center rounded-full border-2',
                      compact ? 'h-6 w-6' : 'h-8 w-8',
                      getStatusColor(event.status)
                    )}
                  >
                    {getStatusIcon(event.status)}
                  </span>
                </div>
                <div className="flex min-w-0 flex-1 justify-between space-x-4 pt-1.5">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className={cn(
                        'font-medium text-gray-900',
                        compact ? 'text-sm' : 'text-base'
                      )}>
                        {event.title}
                      </p>
                      {showSource && event.source && (
                        <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-800">
                          {event.source}
                        </span>
                      )}
                      {showConfidence && event.confidence && (
                        <span className="inline-flex items-center rounded-full bg-primary-100 px-2 py-0.5 text-xs font-medium text-primary-800">
                          {Math.round(event.confidence * 100)}%
                        </span>
                      )}
                    </div>
                    {event.description && (
                      <p className={cn(
                        'text-gray-600',
                        compact ? 'text-xs' : 'text-sm'
                      )}>
                        {event.description}
                      </p>
                    )}
                    {event.user && (
                      <p className={cn(
                        'text-gray-500',
                        compact ? 'text-xs' : 'text-sm'
                      )}>
                        by {event.user}
                      </p>
                    )}
                  </div>
                  <div className={cn(
                    'whitespace-nowrap text-right text-gray-500',
                    compact ? 'text-xs' : 'text-sm'
                  )}>
                    <time dateTime={event.timestamp}>
                      {format(new Date(event.timestamp), compact ? 'MMM d, HH:mm' : 'MMM d, yyyy HH:mm')}
                    </time>
                  </div>
                </div>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

// Compact timeline for sidebars
interface CompactTimelineProps {
  events: TimelineEvent[]
  className?: string
  maxItems?: number
}

export function CompactTimeline({
  events,
  className,
  maxItems = 5,
}: CompactTimelineProps) {
  const recentEvents = events
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, maxItems)

  return (
    <div className={cn('space-y-3', className)}>
      {recentEvents.map((event) => (
        <div key={event.id} className="flex items-start gap-3">
          <div className="flex-shrink-0">
            <div className="flex h-4 w-4 items-center justify-center">
              {event.status === 'success' && (
                <CheckCircleIcon className="h-4 w-4 text-success-500" />
              )}
              {event.status === 'warning' && (
                <ExclamationTriangleIcon className="h-4 w-4 text-warning-500" />
              )}
              {event.status === 'error' && (
                <XCircleIcon className="h-4 w-4 text-error-500" />
              )}
              {event.status === 'pending' && (
                <ClockIcon className="h-4 w-4 text-gray-400" />
              )}
            </div>
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-gray-900 truncate">
              {event.title}
            </p>
            <p className="text-xs text-gray-500">
              {format(new Date(event.timestamp), 'MMM d, HH:mm')}
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}

// Timeline filter component
interface TimelineFilterProps {
  onFilterChange: (filters: {
    status?: string
    source?: string
    dateRange?: { start: string; end: string }
  }) => void
  className?: string
}

export function TimelineFilter({ onFilterChange, className }: TimelineFilterProps) {
  const handleStatusChange = (status: string) => {
    onFilterChange({ status: status === 'all' ? undefined : status })
  }

  const handleSourceChange = (source: string) => {
    onFilterChange({ source: source === 'all' ? undefined : source })
  }

  return (
    <div className={cn('flex gap-4', className)}>
      <div>
        <label htmlFor="status-filter" className="sr-only">
          Filter by status
        </label>
        <select
          id="status-filter"
          className="select text-sm"
          onChange={(e) => handleStatusChange(e.target.value)}
        >
          <option value="all">All Status</option>
          <option value="success">Success</option>
          <option value="warning">Warning</option>
          <option value="error">Error</option>
          <option value="pending">Pending</option>
        </select>
      </div>
      <div>
        <label htmlFor="source-filter" className="sr-only">
          Filter by source
        </label>
        <select
          id="source-filter"
          className="select text-sm"
          onChange={(e) => handleSourceChange(e.target.value)}
        >
          <option value="all">All Sources</option>
          <option value="npi">NPI Registry</option>
          <option value="google_places">Google Places</option>
          <option value="hospital_website">Hospital Website</option>
          <option value="state_board">State Board</option>
          <option value="manual">Manual Review</option>
        </select>
      </div>
    </div>
  )
}
