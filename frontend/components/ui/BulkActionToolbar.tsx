'use client'

import { useState } from 'react'
import { 
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ArrowDownTrayIcon,
  DocumentArrowDownIcon,
  PrinterIcon,
  EnvelopeIcon,
  UserGroupIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'

interface BulkAction {
  id: string
  label: string
  icon: React.ComponentType<any>
  variant: 'primary' | 'secondary' | 'success' | 'warning' | 'error'
  disabled?: boolean
  requiresConfirmation?: boolean
  confirmationMessage?: string
}

interface BulkActionToolbarProps {
  selectedCount: number
  totalCount: number
  onSelectAll: () => void
  onClearSelection: () => void
  onBulkAction: (action: string, selectedIds: string[]) => void
  selectedIds: string[]
  className?: string
}

const defaultActions: BulkAction[] = [
  {
    id: 'accept',
    label: 'Accept Selected',
    icon: CheckCircleIcon,
    variant: 'success',
    requiresConfirmation: true,
    confirmationMessage: 'Are you sure you want to accept all selected providers?'
  },
  {
    id: 'reject',
    label: 'Reject Selected',
    icon: XCircleIcon,
    variant: 'error',
    requiresConfirmation: true,
    confirmationMessage: 'Are you sure you want to reject all selected providers?'
  },
  {
    id: 'flag',
    label: 'Flag for Review',
    icon: ExclamationTriangleIcon,
    variant: 'warning',
    requiresConfirmation: true,
    confirmationMessage: 'Are you sure you want to flag all selected providers for review?'
  },
  {
    id: 'revalidate',
    label: 'Re-validate',
    icon: ArrowPathIcon,
    variant: 'secondary',
    requiresConfirmation: true,
    confirmationMessage: 'Are you sure you want to re-validate all selected providers?'
  },
  {
    id: 'assign',
    label: 'Assign to Reviewer',
    icon: UserGroupIcon,
    variant: 'secondary',
    requiresConfirmation: false
  },
  {
    id: 'contact',
    label: 'Send Email',
    icon: EnvelopeIcon,
    variant: 'secondary',
    requiresConfirmation: false
  },
  {
    id: 'export_csv',
    label: 'Export CSV',
    icon: DocumentArrowDownIcon,
    variant: 'secondary',
    requiresConfirmation: false
  },
  {
    id: 'export_pdf',
    label: 'Export PDF',
    icon: PrinterIcon,
    variant: 'secondary',
    requiresConfirmation: false
  }
]

export function BulkActionToolbar({
  selectedCount,
  totalCount,
  onSelectAll,
  onClearSelection,
  onBulkAction,
  selectedIds,
  className
}: BulkActionToolbarProps) {
  const [showConfirmation, setShowConfirmation] = useState<{
    action: string
    message: string
  } | null>(null)
  const [showAssignModal, setShowAssignModal] = useState(false)
  const [showContactModal, setShowContactModal] = useState(false)

  const handleAction = (action: BulkAction) => {
    if (action.requiresConfirmation) {
      setShowConfirmation({
        action: action.id,
        message: action.confirmationMessage || 'Are you sure?'
      })
    } else {
      onBulkAction(action.id, selectedIds)
    }
  }

  const handleConfirmAction = () => {
    if (showConfirmation) {
      onBulkAction(showConfirmation.action, selectedIds)
      setShowConfirmation(null)
    }
  }

  const handleCancelConfirmation = () => {
    setShowConfirmation(null)
  }

  const getVariantClasses = (variant: BulkAction['variant']) => {
    switch (variant) {
      case 'primary':
        return 'bg-primary-600 hover:bg-primary-700 text-white'
      case 'secondary':
        return 'bg-gray-600 hover:bg-gray-700 text-white'
      case 'success':
        return 'bg-success-600 hover:bg-success-700 text-white'
      case 'warning':
        return 'bg-warning-600 hover:bg-warning-700 text-white'
      case 'error':
        return 'bg-error-600 hover:bg-error-700 text-white'
      default:
        return 'bg-gray-600 hover:bg-gray-700 text-white'
    }
  }

  if (selectedCount === 0) {
    return null
  }

  return (
    <>
      <div className={cn(
        'bg-white border border-gray-200 rounded-lg shadow-sm p-4 mb-4',
        className
      )}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-gray-700">
                {selectedCount} of {totalCount} selected
              </span>
              <button
                onClick={onClearSelection}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Clear
              </button>
            </div>
            
            {selectedCount < totalCount && (
              <button
                onClick={onSelectAll}
                className="text-sm text-primary-600 hover:text-primary-700 font-medium"
              >
                Select All
              </button>
            )}
          </div>

          <div className="flex items-center space-x-2">
            {defaultActions.map((action) => {
              const Icon = action.icon
              return (
                <button
                  key={action.id}
                  onClick={() => handleAction(action)}
                  disabled={action.disabled}
                  className={cn(
                    'inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed',
                    getVariantClasses(action.variant)
                  )}
                  title={action.label}
                >
                  <Icon className="h-4 w-4 mr-1.5" />
                  {action.label}
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showConfirmation && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
            
            <div className="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg">
              <div className="bg-white px-4 pb-4 pt-5 sm:p-6 sm:pb-4">
                <div className="sm:flex sm:items-start">
                  <div className="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-warning-100 sm:mx-0 sm:h-10 sm:w-10">
                    <ExclamationTriangleIcon className="h-6 w-6 text-warning-600" />
                  </div>
                  <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
                    <h3 className="text-base font-semibold leading-6 text-gray-900">
                      Confirm Action
                    </h3>
                    <div className="mt-2">
                      <p className="text-sm text-gray-500">
                        {showConfirmation.message}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6">
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={handleConfirmAction}
                >
                  Confirm
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm mr-3"
                  onClick={handleCancelConfirmation}
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Assign to Reviewer Modal */}
      {showAssignModal && (
        <AssignToReviewerModal
          isOpen={showAssignModal}
          onClose={() => setShowAssignModal(false)}
          onAssign={(reviewerId) => {
            onBulkAction('assign', selectedIds)
            setShowAssignModal(false)
          }}
        />
      )}

      {/* Contact Providers Modal */}
      {showContactModal && (
        <ContactProvidersModal
          isOpen={showContactModal}
          onClose={() => setShowContactModal(false)}
          onSendEmail={(template, subject, body) => {
            onBulkAction('contact', selectedIds)
            setShowContactModal(false)
          }}
        />
      )}
    </>
  )
}

// Assign to Reviewer Modal Component
interface AssignToReviewerModalProps {
  isOpen: boolean
  onClose: () => void
  onAssign: (reviewerId: string) => void
}

function AssignToReviewerModal({ isOpen, onClose, onAssign }: AssignToReviewerModalProps) {
  const [selectedReviewer, setSelectedReviewer] = useState('')

  const reviewers = [
    { id: 'reviewer_001', name: 'John Doe', email: 'john.doe@example.com', role: 'Senior Reviewer' },
    { id: 'reviewer_002', name: 'Jane Smith', email: 'jane.smith@example.com', role: 'Reviewer' },
    { id: 'reviewer_003', name: 'Alice Johnson', email: 'alice.johnson@example.com', role: 'Reviewer' }
  ]

  const handleAssign = () => {
    if (selectedReviewer) {
      onAssign(selectedReviewer)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        
        <div className="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-md">
          <div className="bg-white px-4 pb-4 pt-5 sm:p-6 sm:pb-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium leading-6 text-gray-900">
                Assign to Reviewer
              </h3>
              <button
                type="button"
                className="rounded-md text-gray-400 hover:text-gray-500"
                onClick={onClose}
              >
                <span className="sr-only">Close</span>
                <XCircleIcon className="h-6 w-6" />
              </button>
            </div>

            <div className="space-y-3">
              {reviewers.map((reviewer) => (
                <div
                  key={reviewer.id}
                  className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                    selectedReviewer === reviewer.id
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => setSelectedReviewer(reviewer.id)}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium text-gray-900">{reviewer.name}</div>
                      <div className="text-sm text-gray-500">{reviewer.role}</div>
                    </div>
                    {selectedReviewer === reviewer.id && (
                      <CheckCircleIcon className="h-5 w-5 text-primary-600" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-gray-50 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6">
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={handleAssign}
              disabled={!selectedReviewer}
            >
              Assign
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm mr-3"
              onClick={onClose}
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// Contact Providers Modal Component
interface ContactProvidersModalProps {
  isOpen: boolean
  onClose: () => void
  onSendEmail: (template: string, subject: string, body: string) => void
}

function ContactProvidersModal({ isOpen, onClose, onSendEmail }: ContactProvidersModalProps) {
  const [selectedTemplate, setSelectedTemplate] = useState('verification')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')

  const emailTemplates = {
    verification: {
      subject: 'Provider Information Verification Required',
      body: `Dear Provider,

We are writing to request verification of your provider information in our system. Some details require manual verification to ensure accuracy.

Please review and confirm your information at your earliest convenience.

Best regards,
Provider Validation Team`
    },
    update: {
      subject: 'Provider Information Update Request',
      body: `Dear Provider,

We have identified some inconsistencies in your provider information that require updating.

Please review and update your details within 5 business days to avoid any service interruptions.

Best regards,
Provider Validation Team`
    },
    reminder: {
      subject: 'Reminder: Provider Information Verification',
      body: `Dear Provider,

This is a reminder that we are still waiting for verification of your provider information.

Please review and confirm your details as soon as possible to maintain your active status in our system.

Best regards,
Provider Validation Team`
    }
  }

  const handleTemplateChange = (template: string) => {
    setSelectedTemplate(template)
    setSubject(emailTemplates[template as keyof typeof emailTemplates].subject)
    setBody(emailTemplates[template as keyof typeof emailTemplates].body)
  }

  const handleSend = () => {
    onSendEmail(selectedTemplate, subject, body)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        
        <div className="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-2xl">
          <div className="bg-white px-4 pb-4 pt-5 sm:p-6 sm:pb-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium leading-6 text-gray-900">
                Send Email to Selected Providers
              </h3>
              <button
                type="button"
                className="rounded-md text-gray-400 hover:text-gray-500"
                onClick={onClose}
              >
                <span className="sr-only">Close</span>
                <XCircleIcon className="h-6 w-6" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email Template
                </label>
                <select
                  className="select w-full"
                  value={selectedTemplate}
                  onChange={(e) => handleTemplateChange(e.target.value)}
                >
                  <option value="verification">Verification Request</option>
                  <option value="update">Update Request</option>
                  <option value="reminder">Reminder</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Subject
                </label>
                <input
                  type="text"
                  className="input w-full"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Message
                </label>
                <textarea
                  rows={8}
                  className="input w-full"
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                />
              </div>
            </div>
          </div>

          <div className="bg-gray-50 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6">
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={handleSend}
            >
              Send Email
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm mr-3"
              onClick={onClose}
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}