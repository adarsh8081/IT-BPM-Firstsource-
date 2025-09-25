'use client'

import { useState } from 'react'
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline'
import { cn, maskPhoneNumber, maskEmail, maskSensitiveData } from '@/lib/utils'

interface PrivacyMaskProps {
  value: string
  type: 'phone' | 'email' | 'ssn' | 'generic' | 'npi' | 'license'
  showLastDigits?: number
  showDomain?: boolean
  className?: string
  'aria-label'?: string
}

export function PrivacyMask({
  value,
  type,
  showLastDigits = 4,
  showDomain = true,
  className,
  'aria-label': ariaLabel,
}: PrivacyMaskProps) {
  const [isRevealed, setIsRevealed] = useState(false)
  const [hasPrivilege, setHasPrivilege] = useState(false)

  const toggleReveal = () => {
    // In a real app, this would check user permissions
    // For demo purposes, we'll simulate privilege check
    if (!hasPrivilege) {
      // Simulate privilege check - in real app, this would be an API call
      const hasAccess = window.confirm(
        'This action requires privileged access. Do you have permission to view sensitive data?'
      )
      if (hasAccess) {
        setHasPrivilege(true)
        setIsRevealed(true)
      }
    } else {
      setIsRevealed(!isRevealed)
    }
  }

  const getMaskedValue = () => {
    if (isRevealed || hasPrivilege) {
      return value
    }

    switch (type) {
      case 'phone':
        return maskPhoneNumber(value, showLastDigits)
      case 'email':
        return maskEmail(value, showDomain)
      case 'ssn':
        return maskSensitiveData(value, 'ssn')
      case 'npi':
        return maskSensitiveData(value, 'generic')
      case 'license':
        return maskSensitiveData(value, 'generic')
      default:
        return maskSensitiveData(value, 'generic')
    }
  }

  const getDisplayValue = () => {
    const maskedValue = getMaskedValue()
    
    // Add visual indicator for masked values
    if (!isRevealed && !hasPrivilege) {
      return (
        <span className="relative">
          {maskedValue}
          <span className="absolute -top-1 -right-1 h-2 w-2 bg-warning-500 rounded-full" />
        </span>
      )
    }
    
    return maskedValue
  }

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <span
        className={cn(
          'font-mono text-sm',
          !isRevealed && !hasPrivilege && 'text-gray-600'
        )}
        aria-label={ariaLabel || `${type} value${isRevealed ? ' (revealed)' : ' (masked)'}`}
      >
        {getDisplayValue()}
      </span>
      
      <button
        type="button"
        className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
        onClick={toggleReveal}
        title={isRevealed ? 'Hide sensitive data' : 'Reveal sensitive data'}
        aria-label={isRevealed ? 'Hide sensitive data' : 'Reveal sensitive data'}
      >
        {isRevealed ? (
          <EyeSlashIcon className="h-4 w-4" />
        ) : (
          <EyeIcon className="h-4 w-4" />
        )}
      </button>
    </div>
  )
}

// Conditional privacy mask that respects user permissions
interface ConditionalPrivacyMaskProps extends PrivacyMaskProps {
  userRole?: 'admin' | 'reviewer' | 'viewer'
  requiredRole?: 'admin' | 'reviewer' | 'viewer'
}

export function ConditionalPrivacyMask({
  value,
  type,
  showLastDigits = 4,
  showDomain = true,
  className,
  userRole = 'viewer',
  requiredRole = 'admin',
  'aria-label': ariaLabel,
}: ConditionalPrivacyMaskProps) {
  const roleHierarchy = {
    viewer: 0,
    reviewer: 1,
    admin: 2,
  }

  const hasAccess = roleHierarchy[userRole] >= roleHierarchy[requiredRole]

  if (hasAccess) {
    return (
      <span className={cn('font-mono text-sm', className)}>
        {value}
      </span>
    )
  }

  return (
    <PrivacyMask
      value={value}
      type={type}
      showLastDigits={showLastDigits}
      showDomain={showDomain}
      className={className}
      aria-label={ariaLabel}
    />
  )
}

// Privacy indicator for data sensitivity levels
interface PrivacyIndicatorProps {
  sensitivityLevel: 'low' | 'medium' | 'high' | 'critical'
  className?: string
}

export function PrivacyIndicator({ sensitivityLevel, className }: PrivacyIndicatorProps) {
  const config = {
    low: {
      color: 'text-success-600',
      bgColor: 'bg-success-100',
      icon: '🟢',
      label: 'Low Sensitivity',
    },
    medium: {
      color: 'text-warning-600',
      bgColor: 'bg-warning-100',
      icon: '🟡',
      label: 'Medium Sensitivity',
    },
    high: {
      color: 'text-error-600',
      bgColor: 'bg-error-100',
      icon: '🟠',
      label: 'High Sensitivity',
    },
    critical: {
      color: 'text-red-600',
      bgColor: 'bg-red-100',
      icon: '🔴',
      label: 'Critical Sensitivity',
    },
  }

  const { color, bgColor, icon, label } = config[sensitivityLevel]

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium',
        color,
        bgColor,
        className
      )}
      title={`Data sensitivity: ${label}`}
    >
      <span>{icon}</span>
      <span className="sr-only">{label}</span>
    </span>
  )
}

// Bulk privacy toggle for tables
interface BulkPrivacyToggleProps {
  isRevealed: boolean
  onToggle: (revealed: boolean) => void
  selectedCount: number
  className?: string
}

export function BulkPrivacyToggle({
  isRevealed,
  onToggle,
  selectedCount,
  className,
}: BulkPrivacyToggleProps) {
  const handleToggle = () => {
    if (!isRevealed) {
      // Simulate privilege check for bulk reveal
      const hasAccess = window.confirm(
        `This action requires privileged access to reveal sensitive data for ${selectedCount} items. Do you have permission?`
      )
      if (hasAccess) {
        onToggle(true)
      }
    } else {
      onToggle(false)
    }
  }

  return (
    <button
      type="button"
      className={cn(
        'btn btn-outline btn-sm',
        isRevealed && 'bg-warning-50 border-warning-200 text-warning-700',
        className
      )}
      onClick={handleToggle}
      title={isRevealed ? 'Hide all sensitive data' : 'Reveal all sensitive data'}
    >
      {isRevealed ? (
        <>
          <EyeSlashIcon className="h-4 w-4 mr-1" />
          Hide All
        </>
      ) : (
        <>
          <EyeIcon className="h-4 w-4 mr-1" />
          Reveal All
        </>
      )}
    </button>
  )
}

// Privacy settings panel
interface PrivacySettingsProps {
  userRole: 'admin' | 'reviewer' | 'viewer'
  onRoleChange: (role: 'admin' | 'reviewer' | 'viewer') => void
  className?: string
}

export function PrivacySettings({ userRole, onRoleChange, className }: PrivacySettingsProps) {
  const roles = [
    {
      value: 'viewer',
      label: 'Viewer',
      description: 'Can view basic provider information with masked sensitive data',
      permissions: ['View providers', 'Export reports'],
    },
    {
      value: 'reviewer',
      label: 'Reviewer',
      description: 'Can review providers and access most sensitive data',
      permissions: ['View providers', 'Review providers', 'Access sensitive data', 'Export reports'],
    },
    {
      value: 'admin',
      label: 'Administrator',
      description: 'Full access to all provider data and system functions',
      permissions: ['All viewer permissions', 'All reviewer permissions', 'Manage users', 'System settings'],
    },
  ]

  return (
    <div className={cn('space-y-4', className)}>
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Privacy Settings</h3>
        <p className="text-sm text-gray-600">
          Your current role determines what sensitive data you can access.
        </p>
      </div>

      <div className="space-y-3">
        {roles.map((role) => (
          <label
            key={role.value}
            className={cn(
              'relative flex cursor-pointer rounded-lg p-4 border-2 transition-colors',
              userRole === role.value
                ? 'border-primary-500 bg-primary-50'
                : 'border-gray-200 bg-white hover:bg-gray-50'
            )}
          >
            <input
              type="radio"
              name="user-role"
              value={role.value}
              checked={userRole === role.value}
              onChange={(e) => onRoleChange(e.target.value as any)}
              className="sr-only"
            />
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium text-gray-900">
                    {role.label}
                  </div>
                  <div className="text-sm text-gray-600">
                    {role.description}
                  </div>
                </div>
                <PrivacyIndicator
                  sensitivityLevel={
                    role.value === 'admin' ? 'critical' :
                    role.value === 'reviewer' ? 'high' : 'medium'
                  }
                />
              </div>
              <div className="mt-2">
                <div className="text-xs text-gray-500 mb-1">Permissions:</div>
                <div className="flex flex-wrap gap-1">
                  {role.permissions.map((permission, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-gray-100 text-gray-700"
                    >
                      {permission}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </label>
        ))}
      </div>
    </div>
  )
}
