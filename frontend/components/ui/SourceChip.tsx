'use client'

import { cn } from '@/lib/utils'
import { 
  BuildingOfficeIcon, 
  GlobeAltIcon, 
  DocumentTextIcon, 
  ClipboardDocumentListIcon,
  MagnifyingGlassIcon
} from '@heroicons/react/24/outline'

interface SourceChipProps {
  source: string
  confidence?: number
  size?: 'sm' | 'md' | 'lg'
  variant?: 'default' | 'outline' | 'ghost'
  className?: string
  'aria-label'?: string
}

const sourceConfig = {
  npi: {
    label: 'NPI Registry',
    icon: BuildingOfficeIcon,
    color: 'primary',
    description: 'National Provider Identifier Registry'
  },
  google_places: {
    label: 'Google Places',
    icon: GlobeAltIcon,
    color: 'success',
    description: 'Google Places API'
  },
  hospital_website: {
    label: 'Hospital Website',
    icon: DocumentTextIcon,
    color: 'warning',
    description: 'Hospital or medical facility website'
  },
  state_board: {
    label: 'State Board',
    icon: ClipboardDocumentListIcon,
    color: 'error',
    description: 'State Medical Board'
  },
  enrichment: {
    label: 'Enrichment',
    icon: MagnifyingGlassIcon,
    color: 'gray',
    description: 'Data enrichment service'
  },
  manual: {
    label: 'Manual',
    icon: DocumentTextIcon,
    color: 'gray',
    description: 'Manually entered data'
  },
  ocr: {
    label: 'OCR',
    icon: DocumentTextIcon,
    color: 'warning',
    description: 'Optical Character Recognition'
  }
}

export function SourceChip({
  source,
  confidence,
  size = 'md',
  variant = 'default',
  className,
  'aria-label': ariaLabel,
}: SourceChipProps) {
  const config = sourceConfig[source as keyof typeof sourceConfig] || {
    label: source,
    icon: DocumentTextIcon,
    color: 'gray',
    description: 'Unknown source'
  }

  const Icon = config.icon

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs gap-1',
    md: 'px-2.5 py-1 text-sm gap-1.5',
    lg: 'px-3 py-1.5 text-base gap-2',
  }

  const iconSizes = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
  }

  const getColorClasses = () => {
    const baseColors = {
      primary: 'text-primary-700 bg-primary-100 border-primary-200',
      success: 'text-success-700 bg-success-100 border-success-200',
      warning: 'text-warning-700 bg-warning-100 border-warning-200',
      error: 'text-error-700 bg-error-100 border-error-200',
      gray: 'text-gray-700 bg-gray-100 border-gray-200',
    }

    const outlineColors = {
      primary: 'text-primary-700 bg-transparent border-primary-300 hover:bg-primary-50',
      success: 'text-success-700 bg-transparent border-success-300 hover:bg-success-50',
      warning: 'text-warning-700 bg-transparent border-warning-300 hover:bg-warning-50',
      error: 'text-error-700 bg-transparent border-error-300 hover:bg-error-50',
      gray: 'text-gray-700 bg-transparent border-gray-300 hover:bg-gray-50',
    }

    const ghostColors = {
      primary: 'text-primary-700 bg-transparent hover:bg-primary-50',
      success: 'text-success-700 bg-transparent hover:bg-success-50',
      warning: 'text-warning-700 bg-transparent hover:bg-warning-50',
      error: 'text-error-700 bg-transparent hover:bg-error-50',
      gray: 'text-gray-700 bg-transparent hover:bg-gray-50',
    }

    switch (variant) {
      case 'outline':
        return outlineColors[config.color as keyof typeof outlineColors]
      case 'ghost':
        return ghostColors[config.color as keyof typeof ghostColors]
      default:
        return baseColors[config.color as keyof typeof baseColors]
    }
  }

  const getVariantClasses = () => {
    switch (variant) {
      case 'outline':
        return 'border'
      case 'ghost':
        return 'border-0'
      default:
        return 'border'
    }
  }

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full font-medium transition-colors',
        sizeClasses[size],
        getColorClasses(),
        getVariantClasses(),
        className
      )}
      aria-label={ariaLabel || `${config.label} source${confidence ? ` with ${Math.round(confidence * 100)}% confidence` : ''}`}
      title={config.description}
    >
      <Icon className={iconSizes[size]} aria-hidden="true" />
      <span>{config.label}</span>
      {confidence !== undefined && (
        <span className="text-xs opacity-75">
          {Math.round(confidence * 100)}%
        </span>
      )}
    </span>
  )
}

// Source comparison component
interface SourceComparisonProps {
  sources: Array<{
    source: string
    confidence: number
    value?: string
    timestamp?: string
  }>
  className?: string
}

export function SourceComparison({ sources, className }: SourceComparisonProps) {
  return (
    <div className={cn('space-y-2', className)}>
      {sources.map((sourceData, index) => (
        <div key={index} className="flex items-center justify-between">
          <SourceChip
            source={sourceData.source}
            confidence={sourceData.confidence}
            size="sm"
          />
          <div className="flex items-center gap-2 text-sm text-gray-600">
            {sourceData.value && (
              <span className="truncate max-w-32">{sourceData.value}</span>
            )}
            {sourceData.timestamp && (
              <time className="text-xs text-gray-400">
                {new Date(sourceData.timestamp).toLocaleDateString()}
              </time>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

// Source reliability indicator
interface SourceReliabilityProps {
  source: string
  className?: string
}

export function SourceReliability({ source, className }: SourceReliabilityProps) {
  const reliability = {
    npi: { level: 'high', description: 'Official government registry' },
    google_places: { level: 'high', description: 'Google\'s verified location data' },
    hospital_website: { level: 'medium', description: 'Institutional website data' },
    state_board: { level: 'high', description: 'Official regulatory body' },
    enrichment: { level: 'medium', description: 'Third-party enrichment service' },
    manual: { level: 'low', description: 'Manually entered data' },
    ocr: { level: 'medium', description: 'OCR-extracted data' }
  }

  const config = reliability[source as keyof typeof reliability] || {
    level: 'unknown',
    description: 'Unknown reliability'
  }

  const getReliabilityColor = () => {
    switch (config.level) {
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

  return (
    <div className={cn('flex items-center gap-1', className)}>
      <div className={cn('w-2 h-2 rounded-full', getReliabilityColor().replace('text-', 'bg-'))} />
      <span className={cn('text-xs font-medium', getReliabilityColor())}>
        {config.level.charAt(0).toUpperCase() + config.level.slice(1)} reliability
      </span>
    </div>
  )
}
