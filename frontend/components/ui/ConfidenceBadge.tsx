'use client'

import { cn } from '@/lib/utils'
import { CheckCircleIcon, ExclamationTriangleIcon, XCircleIcon } from '@heroicons/react/24/outline'

interface ConfidenceBadgeProps {
  confidence: number
  size?: 'sm' | 'md' | 'lg'
  showIcon?: boolean
  showText?: boolean
  className?: string
  'aria-label'?: string
}

const confidenceRanges = {
  high: { min: 0.8, max: 1.0, label: 'High', color: 'success' },
  medium: { min: 0.6, max: 0.8, label: 'Medium', color: 'warning' },
  low: { min: 0.0, max: 0.6, label: 'Low', color: 'error' },
}

export function ConfidenceBadge({
  confidence,
  size = 'md',
  showIcon = true,
  showText = true,
  className,
  'aria-label': ariaLabel,
}: ConfidenceBadgeProps) {
  const range = confidence >= 0.8 ? 'high' : confidence >= 0.6 ? 'medium' : 'low'
  const { label, color } = confidenceRanges[range]
  const percentage = Math.round(confidence * 100)

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base',
  }

  const iconSizes = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
  }

  const getIcon = () => {
    if (!showIcon) return null
    
    const iconClass = cn(iconSizes[size])
    
    switch (range) {
      case 'high':
        return <CheckCircleIcon className={iconClass} aria-hidden="true" />
      case 'medium':
        return <ExclamationTriangleIcon className={iconClass} aria-hidden="true" />
      case 'low':
        return <XCircleIcon className={iconClass} aria-hidden="true" />
      default:
        return null
    }
  }

  const getColorClasses = () => {
    switch (color) {
      case 'success':
        return 'bg-success-100 text-success-800 border-success-200'
      case 'warning':
        return 'bg-warning-100 text-warning-800 border-warning-200'
      case 'error':
        return 'bg-error-100 text-error-800 border-error-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border font-medium',
        sizeClasses[size],
        getColorClasses(),
        className
      )}
      aria-label={ariaLabel || `Confidence: ${percentage}% (${label})`}
      role="img"
    >
      {getIcon()}
      {showText && (
        <span>
          {percentage}%
          <span className="sr-only"> confidence ({label})</span>
        </span>
      )}
    </span>
  )
}

// Progress bar variant
interface ConfidenceProgressProps {
  confidence: number
  className?: string
  showLabel?: boolean
  'aria-label'?: string
}

export function ConfidenceProgress({
  confidence,
  className,
  showLabel = true,
  'aria-label': ariaLabel,
}: ConfidenceProgressProps) {
  const percentage = Math.round(confidence * 100)
  const range = confidence >= 0.8 ? 'high' : confidence >= 0.6 ? 'medium' : 'low'
  
  const getProgressColor = () => {
    switch (range) {
      case 'high':
        return 'bg-success-500'
      case 'medium':
        return 'bg-warning-500'
      case 'low':
        return 'bg-error-500'
      default:
        return 'bg-gray-500'
    }
  }

  return (
    <div className={cn('w-full', className)}>
      {showLabel && (
        <div className="flex justify-between text-xs text-gray-600 mb-1">
          <span>Confidence</span>
          <span>{percentage}%</span>
        </div>
      )}
      <div
        className="w-full bg-gray-200 rounded-full h-2"
        role="progressbar"
        aria-valuenow={percentage}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={ariaLabel || `Confidence level: ${percentage} percent`}
      >
        <div
          className={cn(
            'h-2 rounded-full transition-all duration-300 ease-in-out',
            getProgressColor()
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}

// Confidence meter for detailed views
interface ConfidenceMeterProps {
  confidence: number
  label?: string
  className?: string
  showPercentage?: boolean
}

export function ConfidenceMeter({
  confidence,
  label = 'Confidence',
  className,
  showPercentage = true,
}: ConfidenceMeterProps) {
  const percentage = Math.round(confidence * 100)
  const range = confidence >= 0.8 ? 'high' : confidence >= 0.6 ? 'medium' : 'low'
  
  const getMeterColor = () => {
    switch (range) {
      case 'high':
        return 'text-success-600'
      case 'medium':
        return 'text-warning-600'
      case 'low':
        return 'text-error-600'
      default:
        return 'text-gray-600'
    }
  }

  const getMeterBgColor = () => {
    switch (range) {
      case 'high':
        return 'bg-success-100'
      case 'medium':
        return 'bg-warning-100'
      case 'low':
        return 'bg-error-100'
      default:
        return 'bg-gray-100'
    }
  }

  return (
    <div className={cn('flex items-center gap-3', className)}>
      <div className="flex-1">
        <div className="flex justify-between text-sm font-medium text-gray-700 mb-1">
          <span>{label}</span>
          {showPercentage && (
            <span className={getMeterColor()}>{percentage}%</span>
          )}
        </div>
        <div className={cn('w-full h-2 rounded-full', getMeterBgColor())}>
          <div
            className={cn(
              'h-2 rounded-full transition-all duration-500 ease-in-out',
              getMeterColor().replace('text-', 'bg-')
            )}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    </div>
  )
}
