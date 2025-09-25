'use client'

import { useState } from 'react'
import { useQuery } from 'react-query'
import { 
  ClipboardDocumentListIcon,
  UserGroupIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  EnvelopeIcon,
  PlusIcon
} from '@heroicons/react/24/outline'
import { formatNumber, formatDate } from '@/lib/utils'
import { ConfidenceBadge } from '@/components/ui/ConfidenceBadge'
import { PrivacyMask } from '@/components/ui/PrivacyMask'
import { ManualReviewModal } from '@/components/ui/ManualReviewModal'

// Mock data - in real app, this would come from API
const mockReviewQueue = {
  assignedToMe: [
    {
      id: 'provider_001',
      providerId: 'PROV000001',
      givenName: 'Dr. Sarah',
      familyName: 'Johnson',
      npiNumber: '1234567890',
      email: 'sarah.johnson@example.com',
      phonePrimary: '+1-555-123-4567',
      practiceName: 'San Francisco Medical Group',
      overallConfidence: 0.65,
      validationStatus: 'warning',
      flags: ['LOW_CONFIDENCE_EMAIL', 'MISSING_LICENSE_VERIFICATION'],
      assignedAt: '2024-01-15T09:00:00Z',
      priority: 'high',
      assignedBy: 'John Doe',
      notes: 'Email validation failed, needs manual verification',
      reviewerNotes: ''
    },
    {
      id: 'provider_002',
      providerId: 'PROV000002',
      givenName: 'Dr. Michael',
      familyName: 'Brown',
      npiNumber: '0987654321',
      email: 'michael.brown@example.com',
      phonePrimary: '+1-555-987-6543',
      practiceName: 'Downtown Medical Center',
      overallConfidence: 0.45,
      validationStatus: 'invalid',
      flags: ['INVALID_NPI', 'MISSING_ADDRESS'],
      assignedAt: '2024-01-15T08:30:00Z',
      priority: 'critical',
      assignedBy: 'Jane Smith',
      notes: 'NPI validation failed, address missing',
      reviewerNotes: ''
    }
  ],
  
  allAssigned: [
    {
      id: 'provider_003',
      providerId: 'PROV000003',
      givenName: 'Dr. Emily',
      familyName: 'Davis',
      npiNumber: '1122334455',
      email: 'emily.davis@example.com',
      phonePrimary: '+1-555-555-5555',
      practiceName: 'City Medical Group',
      overallConfidence: 0.72,
      validationStatus: 'warning',
      flags: ['LOW_CONFIDENCE_PHONE'],
      assignedAt: '2024-01-15T07:15:00Z',
      priority: 'medium',
      assignedBy: 'Bob Wilson',
      assignedTo: 'Alice Johnson',
      notes: 'Phone number validation inconclusive',
      reviewerNotes: 'Contacted provider, waiting for response'
    }
  ],
  
  reviewers: [
    {
      id: 'reviewer_001',
      name: 'John Doe',
      email: 'john.doe@example.com',
      role: 'Senior Reviewer',
      assignedCount: 5,
      completedToday: 3,
      averageTime: 12.5,
      status: 'active'
    },
    {
      id: 'reviewer_002',
      name: 'Jane Smith',
      email: 'jane.smith@example.com',
      role: 'Reviewer',
      assignedCount: 3,
      completedToday: 2,
      averageTime: 18.2,
      status: 'active'
    },
    {
      id: 'reviewer_003',
      name: 'Alice Johnson',
      email: 'alice.johnson@example.com',
      role: 'Reviewer',
      assignedCount: 2,
      completedToday: 1,
      averageTime: 15.8,
      status: 'busy'
    }
  ]
}

interface ReviewerCardProps {
  reviewer: typeof mockReviewQueue.reviewers[0]
  onAssign: (reviewerId: string) => void
}

function ReviewerCard({ reviewer, onAssign }: ReviewerCardProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'text-success-600 bg-success-100'
      case 'busy':
        return 'text-warning-600 bg-warning-100'
      case 'offline':
        return 'text-gray-600 bg-gray-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0 h-10 w-10">
            <div className="h-10 w-10 rounded-full bg-primary-100 flex items-center justify-center">
              <span className="text-sm font-medium text-primary-700">
                {reviewer.name.split(' ').map(n => n[0]).join('')}
              </span>
            </div>
          </div>
          <div>
            <div className="text-sm font-medium text-gray-900">
              {reviewer.name}
            </div>
            <div className="text-sm text-gray-500">
              {reviewer.role}
            </div>
          </div>
        </div>
        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(reviewer.status)}`}>
          {reviewer.status}
        </span>
      </div>
      
      <div className="grid grid-cols-3 gap-4 text-center mb-4">
        <div>
          <div className="text-lg font-semibold text-gray-900">
            {reviewer.assignedCount}
          </div>
          <div className="text-xs text-gray-500">Assigned</div>
        </div>
        <div>
          <div className="text-lg font-semibold text-gray-900">
            {reviewer.completedToday}
          </div>
          <div className="text-xs text-gray-500">Completed</div>
        </div>
        <div>
          <div className="text-lg font-semibold text-gray-900">
            {reviewer.averageTime}m
          </div>
          <div className="text-xs text-gray-500">Avg Time</div>
        </div>
      </div>
      
      <button
        onClick={() => onAssign(reviewer.id)}
        className="w-full btn btn-outline btn-sm"
        disabled={reviewer.status === 'offline'}
      >
        Assign Provider
      </button>
    </div>
  )
}

interface ReviewItemProps {
  provider: any
  onReview: (provider: any) => void
  onReassign: (providerId: string) => void
  onContact: (provider: any) => void
}

function ReviewItem({ provider, onReview, onReassign, onContact }: ReviewItemProps) {
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'text-error-600 bg-error-100'
      case 'high':
        return 'text-warning-600 bg-warning-100'
      case 'medium':
        return 'text-blue-600 bg-blue-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h4 className="text-sm font-medium text-gray-900">
              {provider.givenName} {provider.familyName}
            </h4>
            <ConfidenceBadge confidence={provider.overallConfidence} size="sm" />
            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(provider.priority)}`}>
              {provider.priority}
            </span>
          </div>
          
          <div className="text-sm text-gray-600 mb-2">
            <div>Provider ID: {provider.providerId}</div>
            <div>Practice: {provider.practiceName}</div>
            <div>Assigned: {formatDate(provider.assignedAt, 'relative')}</div>
            {provider.assignedTo && (
              <div>Assigned to: {provider.assignedTo}</div>
            )}
          </div>
          
          <div className="flex flex-wrap gap-1 mb-3">
            {provider.flags.map((flag: string, index: number) => (
              <span key={index} className="badge badge-warning text-xs">
                {flag.replace('_', ' ')}
              </span>
            ))}
          </div>
          
          {provider.notes && (
            <div className="text-sm text-gray-600 bg-gray-50 p-2 rounded mb-3">
              <strong>Notes:</strong> {provider.notes}
            </div>
          )}
          
          {provider.reviewerNotes && (
            <div className="text-sm text-blue-600 bg-blue-50 p-2 rounded mb-3">
              <strong>Reviewer Notes:</strong> {provider.reviewerNotes}
            </div>
          )}
        </div>
      </div>
      
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <PrivacyMask value={provider.email} type="email" />
          <PrivacyMask value={provider.phonePrimary} type="phone" />
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={() => onContact(provider)}
            className="btn btn-outline btn-sm"
            title="Contact provider"
          >
            <EnvelopeIcon className="h-4 w-4" />
          </button>
          <button
            onClick={() => onReassign(provider.id)}
            className="btn btn-outline btn-sm"
            title="Reassign to another reviewer"
          >
            <UserGroupIcon className="h-4 w-4" />
          </button>
          <button
            onClick={() => onReview(provider)}
            className="btn btn-primary btn-sm"
            title="Review provider"
          >
            Review
          </button>
        </div>
      </div>
    </div>
  )
}

export function ManualReviewQueue() {
  const [activeTab, setActiveTab] = useState<'assigned' | 'all' | 'reviewers'>('assigned')
  const [showReviewModal, setShowReviewModal] = useState(false)
  const [reviewProvider, setReviewProvider] = useState<any>(null)
  const [showContactModal, setShowContactModal] = useState(false)
  const [contactProvider, setContactProvider] = useState<any>(null)

  const { data: reviewData, isLoading, error } = useQuery(
    'review-queue',
    async () => {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 500))
      return mockReviewQueue
    },
    {
      refetchInterval: 30 * 1000, // 30 seconds
    }
  )

  const handleReviewAction = async (action: 'accept' | 'reject' | 'request_verification', note?: string) => {
    // Implement review action logic
    console.log('Review action:', action, reviewProvider?.id, note)
    setShowReviewModal(false)
    setReviewProvider(null)
  }

  const handleReassign = (providerId: string) => {
    // Implement reassignment logic
    console.log('Reassign provider:', providerId)
  }

  const handleAssignToReviewer = (reviewerId: string) => {
    // Implement assignment logic
    console.log('Assign to reviewer:', reviewerId)
  }

  const handleContactProvider = (provider: any) => {
    setContactProvider(provider)
    setShowContactModal(true)
  }

  const handleSendEmail = async (template: string, subject: string, body: string) => {
    // Implement email sending logic
    console.log('Send email to:', contactProvider?.email, { template, subject, body })
    setShowContactModal(false)
    setContactProvider(null)
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="loading-spinner mx-auto mb-4" />
          <p className="text-gray-600">Loading review queue...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-900 font-medium mb-2">Error loading review queue</p>
          <p className="text-gray-600">Please try refreshing the page</p>
        </div>
      </div>
    )
  }

  const { assignedToMe, allAssigned, reviewers } = reviewData!

  const tabs = [
    {
      id: 'assigned',
      name: 'Assigned to Me',
      count: assignedToMe.length,
      icon: ClipboardDocumentListIcon,
    },
    {
      id: 'all',
      name: 'All Assigned',
      count: allAssigned.length,
      icon: UserGroupIcon,
    },
    {
      id: 'reviewers',
      name: 'Reviewers',
      count: reviewers.length,
      icon: UserGroupIcon,
    },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Manual Review Queue</h1>
          <p className="mt-2 text-gray-600">
            Manage provider reviews and reviewer assignments
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <ClipboardDocumentListIcon className="h-6 w-6 text-gray-400" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Assigned to Me
                    </dt>
                    <dd className="text-lg font-medium text-gray-900">
                      {assignedToMe.length}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <UserGroupIcon className="h-6 w-6 text-gray-400" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Total Assigned
                    </dt>
                    <dd className="text-lg font-medium text-gray-900">
                      {assignedToMe.length + allAssigned.length}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <ClockIcon className="h-6 w-6 text-gray-400" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Avg Review Time
                    </dt>
                    <dd className="text-lg font-medium text-gray-900">
                      15.2m
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <CheckCircleIcon className="h-6 w-6 text-gray-400" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Completed Today
                    </dt>
                    <dd className="text-lg font-medium text-gray-900">
                      {reviewers.reduce((sum, r) => sum + r.completedToday, 0)}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`${
                    activeTab === tab.id
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  } whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm flex items-center gap-2`}
                >
                  <Icon className="h-4 w-4" />
                  {tab.name}
                  <span className={`ml-2 py-0.5 px-2 rounded-full text-xs ${
                    activeTab === tab.id
                      ? 'bg-primary-100 text-primary-600'
                      : 'bg-gray-100 text-gray-600'
                  }`}>
                    {tab.count}
                  </span>
                </button>
              )
            })}
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'assigned' && (
          <div className="space-y-4">
            {assignedToMe.length === 0 ? (
              <div className="text-center py-12">
                <ClipboardDocumentListIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No providers assigned</h3>
                <p className="mt-1 text-sm text-gray-500">
                  You don't have any providers assigned for review.
                </p>
              </div>
            ) : (
              assignedToMe.map((provider) => (
                <ReviewItem
                  key={provider.id}
                  provider={provider}
                  onReview={(provider) => {
                    setReviewProvider(provider)
                    setShowReviewModal(true)
                  }}
                  onReassign={handleReassign}
                  onContact={handleContactProvider}
                />
              ))
            )}
          </div>
        )}

        {activeTab === 'all' && (
          <div className="space-y-4">
            {allAssigned.length === 0 ? (
              <div className="text-center py-12">
                <UserGroupIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No providers assigned</h3>
                <p className="mt-1 text-sm text-gray-500">
                  No providers are currently assigned for review.
                </p>
              </div>
            ) : (
              allAssigned.map((provider) => (
                <ReviewItem
                  key={provider.id}
                  provider={provider}
                  onReview={(provider) => {
                    setReviewProvider(provider)
                    setShowReviewModal(true)
                  }}
                  onReassign={handleReassign}
                  onContact={handleContactProvider}
                />
              ))
            )}
          </div>
        )}

        {activeTab === 'reviewers' && (
          <div>
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-lg font-medium text-gray-900">Reviewers</h3>
              <button className="btn btn-primary">
                <PlusIcon className="h-4 w-4 mr-2" />
                Add Reviewer
              </button>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {reviewers.map((reviewer) => (
                <ReviewerCard
                  key={reviewer.id}
                  reviewer={reviewer}
                  onAssign={handleAssignToReviewer}
                />
              ))}
            </div>
          </div>
        )}

        {/* Manual Review Modal */}
        {showReviewModal && reviewProvider && (
          <ManualReviewModal
            isOpen={showReviewModal}
            onClose={() => {
              setShowReviewModal(false)
              setReviewProvider(null)
            }}
            provider={{
              id: reviewProvider.id,
              name: `${reviewProvider.givenName} ${reviewProvider.familyName}`,
              npi: reviewProvider.npiNumber,
              overallConfidence: reviewProvider.overallConfidence,
              validationStatus: reviewProvider.validationStatus,
              flags: reviewProvider.flags,
            }}
            onAction={handleReviewAction}
          />
        )}

        {/* Contact Provider Modal */}
        {showContactModal && contactProvider && (
          <ContactProviderModal
            isOpen={showContactModal}
            onClose={() => {
              setShowContactModal(false)
              setContactProvider(null)
            }}
            provider={contactProvider}
            onSendEmail={handleSendEmail}
          />
        )}
      </div>
    </div>
  )
}

// Contact Provider Modal Component
interface ContactProviderModalProps {
  isOpen: boolean
  onClose: () => void
  provider: any
  onSendEmail: (template: string, subject: string, body: string) => void
}

function ContactProviderModal({ isOpen, onClose, provider, onSendEmail }: ContactProviderModalProps) {
  const [selectedTemplate, setSelectedTemplate] = useState('verification')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')

  const emailTemplates = {
    verification: {
      subject: 'Provider Information Verification Required',
      body: `Dear ${provider.givenName} ${provider.familyName},

We are writing to request verification of your provider information in our system. Some details require manual verification to ensure accuracy.

Please review and confirm the following information:
- Contact Information
- Practice Address
- License Details

If you have any questions or need to update any information, please contact us at your earliest convenience.

Best regards,
Provider Validation Team`
    },
    update: {
      subject: 'Provider Information Update Request',
      body: `Dear ${provider.givenName} ${provider.familyName},

We have identified some inconsistencies in your provider information that require updating.

Please review and update the following:
- Contact Information
- Practice Details
- License Information

Please respond within 5 business days to avoid any service interruptions.

Best regards,
Provider Validation Team`
    },
    reminder: {
      subject: 'Reminder: Provider Information Verification',
      body: `Dear ${provider.givenName} ${provider.familyName},

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
                Contact Provider
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

            <div className="mb-4 p-3 bg-gray-50 rounded-lg">
              <div className="text-sm font-medium text-gray-900">
                {provider.givenName} {provider.familyName}
              </div>
              <div className="text-sm text-gray-600">
                {provider.email}
              </div>
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
