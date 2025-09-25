'use client'

import { useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { Fragment } from 'react'
import { XMarkIcon, CheckCircleIcon, XCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'

interface ManualReviewModalProps {
  isOpen: boolean
  onClose: () => void
  provider: {
    id: string
    name: string
    npi?: string
    overallConfidence: number
    validationStatus: string
    flags: string[]
  }
  onAction: (action: 'accept' | 'reject' | 'request_verification', note?: string) => void
  className?: string
}

export function ManualReviewModal({
  isOpen,
  onClose,
  provider,
  onAction,
  className,
}: ManualReviewModalProps) {
  const [selectedAction, setSelectedAction] = useState<'accept' | 'reject' | 'request_verification'>('accept')
  const [note, setNote] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async () => {
    setIsSubmitting(true)
    try {
      await onAction(selectedAction, note)
      onClose()
      setNote('')
      setSelectedAction('accept')
    } catch (error) {
      console.error('Error submitting review action:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleClose = () => {
    if (!isSubmitting) {
      onClose()
      setNote('')
      setSelectedAction('accept')
    }
  }

  const actionOptions = [
    {
      value: 'accept',
      label: 'Accept Provider',
      description: 'Approve this provider for inclusion in the directory',
      icon: CheckCircleIcon,
      color: 'text-success-600',
      bgColor: 'bg-success-50',
      borderColor: 'border-success-200',
    },
    {
      value: 'reject',
      label: 'Reject Provider',
      description: 'Reject this provider due to validation issues',
      icon: XCircleIcon,
      color: 'text-error-600',
      bgColor: 'bg-error-50',
      borderColor: 'border-error-200',
    },
    {
      value: 'request_verification',
      label: 'Request Manual Verification',
      description: 'Request additional verification from the provider',
      icon: ExclamationTriangleIcon,
      color: 'text-warning-600',
      bgColor: 'bg-warning-50',
      borderColor: 'border-warning-200',
    },
  ]

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={handleClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-25" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className={cn(
                'w-full max-w-2xl transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all',
                className
              )}>
                <div className="flex items-center justify-between mb-4">
                  <Dialog.Title
                    as="h3"
                    className="text-lg font-medium leading-6 text-gray-900"
                  >
                    Manual Review - {provider.name}
                  </Dialog.Title>
                  <button
                    type="button"
                    className="rounded-md text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    onClick={handleClose}
                    disabled={isSubmitting}
                  >
                    <span className="sr-only">Close</span>
                    <XMarkIcon className="h-6 w-6" aria-hidden="true" />
                  </button>
                </div>

                {/* Provider Summary */}
                <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="font-medium text-gray-700">Provider ID:</span>
                      <p className="text-gray-900">{provider.id}</p>
                    </div>
                    {provider.npi && (
                      <div>
                        <span className="font-medium text-gray-700">NPI:</span>
                        <p className="text-gray-900">{provider.npi}</p>
                      </div>
                    )}
                    <div>
                      <span className="font-medium text-gray-700">Overall Confidence:</span>
                      <p className="text-gray-900">{Math.round(provider.overallConfidence * 100)}%</p>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700">Status:</span>
                      <p className="text-gray-900 capitalize">{provider.validationStatus}</p>
                    </div>
                  </div>
                  {provider.flags.length > 0 && (
                    <div className="mt-3">
                      <span className="font-medium text-gray-700">Flags:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {provider.flags.map((flag, index) => (
                          <span
                            key={index}
                            className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-warning-100 text-warning-800"
                          >
                            {flag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Action Selection */}
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Select Action
                  </label>
                  <div className="space-y-3">
                    {actionOptions.map((option) => {
                      const Icon = option.icon
                      return (
                        <label
                          key={option.value}
                          className={cn(
                            'relative flex cursor-pointer rounded-lg p-4 border-2 transition-colors',
                            selectedAction === option.value
                              ? `${option.bgColor} ${option.borderColor}`
                              : 'bg-white border-gray-200 hover:bg-gray-50'
                          )}
                        >
                          <input
                            type="radio"
                            name="action"
                            value={option.value}
                            checked={selectedAction === option.value}
                            onChange={(e) => setSelectedAction(e.target.value as any)}
                            className="sr-only"
                          />
                          <div className="flex items-start">
                            <Icon className={cn('h-5 w-5 mt-0.5', option.color)} />
                            <div className="ml-3">
                              <div className="text-sm font-medium text-gray-900">
                                {option.label}
                              </div>
                              <div className="text-sm text-gray-500">
                                {option.description}
                              </div>
                            </div>
                          </div>
                        </label>
                      )
                    })}
                  </div>
                </div>

                {/* Note Section */}
                <div className="mb-6">
                  <label htmlFor="review-note" className="block text-sm font-medium text-gray-700 mb-2">
                    Review Notes {selectedAction === 'reject' && <span className="text-error-500">*</span>}
                  </label>
                  <textarea
                    id="review-note"
                    rows={4}
                    className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                    placeholder={
                      selectedAction === 'accept'
                        ? 'Optional notes about why this provider was accepted...'
                        : selectedAction === 'reject'
                        ? 'Please explain why this provider was rejected...'
                        : 'Please specify what additional verification is needed...'
                    }
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    required={selectedAction === 'reject'}
                  />
                  <p className="mt-2 text-sm text-gray-500">
                    {selectedAction === 'accept' && 'Notes are optional for accepted providers.'}
                    {selectedAction === 'reject' && 'Notes are required when rejecting a provider.'}
                    {selectedAction === 'request_verification' && 'Specify what information needs to be verified.'}
                  </p>
                </div>

                {/* Action Buttons */}
                <div className="flex justify-end gap-3">
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleClose}
                    disabled={isSubmitting}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    className={cn(
                      'btn',
                      selectedAction === 'accept' && 'btn-success',
                      selectedAction === 'reject' && 'btn-error',
                      selectedAction === 'request_verification' && 'btn-warning'
                    )}
                    onClick={handleSubmit}
                    disabled={isSubmitting || (selectedAction === 'reject' && !note.trim())}
                  >
                    {isSubmitting && (
                      <div className="loading-spinner mr-2" />
                    )}
                    {selectedAction === 'accept' && 'Accept Provider'}
                    {selectedAction === 'reject' && 'Reject Provider'}
                    {selectedAction === 'request_verification' && 'Request Verification'}
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}

// Quick review modal for simple actions
interface QuickReviewModalProps {
  isOpen: boolean
  onClose: () => void
  provider: {
    id: string
    name: string
  }
  onQuickAction: (action: 'accept' | 'reject') => void
}

export function QuickReviewModal({
  isOpen,
  onClose,
  provider,
  onQuickAction,
}: QuickReviewModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleAction = async (action: 'accept' | 'reject') => {
    setIsSubmitting(true)
    try {
      await onQuickAction(action)
      onClose()
    } catch (error) {
      console.error('Error submitting quick review action:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-25" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
                <Dialog.Title
                  as="h3"
                  className="text-lg font-medium leading-6 text-gray-900 mb-4"
                >
                  Quick Review - {provider.name}
                </Dialog.Title>

                <p className="text-sm text-gray-600 mb-6">
                  Choose an action for this provider:
                </p>

                <div className="flex gap-3">
                  <button
                    type="button"
                    className="flex-1 btn btn-success"
                    onClick={() => handleAction('accept')}
                    disabled={isSubmitting}
                  >
                    <CheckCircleIcon className="h-4 w-4 mr-2" />
                    Accept
                  </button>
                  <button
                    type="button"
                    className="flex-1 btn btn-error"
                    onClick={() => handleAction('reject')}
                    disabled={isSubmitting}
                  >
                    <XCircleIcon className="h-4 w-4 mr-2" />
                    Reject
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}
