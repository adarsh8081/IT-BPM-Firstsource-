'use client'

import { useState, useEffect } from 'react'
import { useQuery } from 'react-query'
import { useRouter } from 'next/navigation'
import { 
  ArrowLeftIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  PencilIcon,
  ArrowPathIcon,
  DocumentTextIcon,
  PrinterIcon
} from '@heroicons/react/24/outline'
import { formatDate, formatPercentage } from '@/lib/utils'
import { ConfidenceBadge, ConfidenceProgress, ConfidenceMeter } from '@/components/ui/ConfidenceBadge'
import { SourceChip, SourceComparison, SourceReliability } from '@/components/ui/SourceChip'
import { Timeline } from '@/components/ui/Timeline'
import { PrivacyMask } from '@/components/ui/PrivacyMask'
import { ManualReviewModal } from '@/components/ui/ManualReviewModal'

// Mock data - in real app, this would come from API
const mockProviderDetail = {
  id: 'provider_123',
  providerId: 'PROV000123',
  givenName: 'Dr. Sarah',
  familyName: 'Johnson',
  npiNumber: '1234567890',
  phonePrimary: '+1-555-123-4567',
  email: 'sarah.johnson@example.com',
  addressStreet: '123 Main Street',
  addressCity: 'San Francisco',
  addressState: 'CA',
  addressZip: '94102',
  licenseNumber: 'LIC123456',
  licenseState: 'CA',
  licenseStatus: 'ACTIVE',
  primaryTaxonomy: 'Internal Medicine',
  practiceName: 'San Francisco Medical Group',
  overallConfidence: 0.89,
  validationStatus: 'valid',
  flags: ['LOW_CONFIDENCE_EMAIL'],
  lastValidatedAt: '2024-01-15T10:30:00Z',
  createdAt: '2024-01-10T08:00:00Z',
  
  fieldAnalyses: [
    {
      fieldName: 'npi_number',
      originalValue: '1234567890',
      validatedValue: '1234567890',
      confidence: 0.95,
      validationStatus: 'valid',
      validationSource: 'npi',
      validationTimestamp: '2024-01-15T10:30:00Z',
      issues: [],
      suggestions: []
    },
    {
      fieldName: 'given_name',
      originalValue: 'Sarah',
      validatedValue: 'Sarah',
      confidence: 0.92,
      validationStatus: 'valid',
      validationSource: 'npi',
      validationTimestamp: '2024-01-15T10:30:00Z',
      issues: [],
      suggestions: []
    },
    {
      fieldName: 'family_name',
      originalValue: 'Johnson',
      validatedValue: 'Johnson',
      confidence: 0.92,
      validationStatus: 'valid',
      validationSource: 'npi',
      validationTimestamp: '2024-01-15T10:30:00Z',
      issues: [],
      suggestions: []
    },
    {
      fieldName: 'phone_primary',
      originalValue: '(555) 123-4567',
      validatedValue: '+15551234567',
      confidence: 0.88,
      validationStatus: 'valid',
      validationSource: 'enrichment',
      validationTimestamp: '2024-01-15T10:30:00Z',
      issues: [],
      suggestions: []
    },
    {
      fieldName: 'email',
      originalValue: 'sarah.johnson@example.com',
      validatedValue: 'sarah.johnson@example.com',
      confidence: 0.65,
      validationStatus: 'warning',
      validationSource: 'manual',
      validationTimestamp: '2024-01-15T10:30:00Z',
      issues: ['Low MX record confidence'],
      suggestions: ['Verify email address with provider']
    },
    {
      fieldName: 'address_street',
      originalValue: '123 Main St',
      validatedValue: '123 Main Street',
      confidence: 0.91,
      validationStatus: 'valid',
      validationSource: 'google_places',
      validationTimestamp: '2024-01-15T10:30:00Z',
      issues: [],
      suggestions: []
    },
    {
      fieldName: 'license_number',
      originalValue: 'LIC123456',
      validatedValue: 'LIC123456',
      confidence: 0.94,
      validationStatus: 'valid',
      validationSource: 'state_board',
      validationTimestamp: '2024-01-15T10:30:00Z',
      issues: [],
      suggestions: []
    }
  ],
  
  sources: [
    {
      source: 'npi',
      confidence: 0.92,
      value: 'Official NPI Registry data',
      timestamp: '2024-01-15T10:30:00Z'
    },
    {
      source: 'google_places',
      confidence: 0.91,
      value: 'Google Places API validation',
      timestamp: '2024-01-15T10:30:00Z'
    },
    {
      source: 'state_board',
      confidence: 0.94,
      value: 'California Medical Board',
      timestamp: '2024-01-15T10:30:00Z'
    },
    {
      source: 'enrichment',
      confidence: 0.88,
      value: 'Data enrichment service',
      timestamp: '2024-01-15T10:30:00Z'
    }
  ],
  
  timeline: [
    {
      id: '1',
      type: 'validation',
      title: 'Initial validation completed',
      description: 'Provider data validated through automated process',
      timestamp: '2024-01-15T10:30:00Z',
      status: 'success',
      source: 'system',
      confidence: 0.89,
      user: 'System'
    },
    {
      id: '2',
      type: 'review',
      title: 'Manual review initiated',
      description: 'Provider flagged for manual review due to low email confidence',
      timestamp: '2024-01-15T11:00:00Z',
      status: 'warning',
      source: 'manual_review',
      confidence: 0.65,
      user: 'John Doe'
    },
    {
      id: '3',
      type: 'update',
      title: 'Address validated',
      description: 'Address successfully validated through Google Places API',
      timestamp: '2024-01-15T10:35:00Z',
      status: 'success',
      source: 'google_places',
      confidence: 0.91,
      user: 'System'
    },
    {
      id: '4',
      type: 'validation',
      title: 'License verified',
      description: 'Medical license verified as active with California Medical Board',
      timestamp: '2024-01-15T10:32:00Z',
      status: 'success',
      source: 'state_board',
      confidence: 0.94,
      user: 'System'
    }
  ],
  
  recommendations: [
    'Verify email address with provider to improve confidence score',
    'Consider requesting updated contact information',
    'Monitor for any changes in license status'
  ]
}

interface FieldAnalysisProps {
  field: any
}

function FieldAnalysis({ field }: FieldAnalysisProps) {
  const [showDetails, setShowDetails] = useState(false)

  return (
    <div className="border border-gray-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <h4 className="text-sm font-medium text-gray-900 capitalize">
            {field.fieldName.replace('_', ' ')}
          </h4>
          <ConfidenceBadge confidence={field.confidence} size="sm" />
          <span className={`badge ${
            field.validationStatus === 'valid' ? 'badge-success' :
            field.validationStatus === 'warning' ? 'badge-warning' :
            'badge-error'
          }`}>
            {field.validationStatus}
          </span>
        </div>
        <button
          type="button"
          className="text-sm text-primary-600 hover:text-primary-700"
          onClick={() => setShowDetails(!showDetails)}
        >
          {showDetails ? 'Hide' : 'Show'} Details
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Original Value
          </label>
          <div className="text-sm text-gray-900 font-mono">
            {field.fieldName === 'phone_primary' ? (
              <PrivacyMask value={field.originalValue} type="phone" />
            ) : field.fieldName === 'email' ? (
              <PrivacyMask value={field.originalValue} type="email" />
            ) : field.fieldName === 'npi_number' ? (
              <PrivacyMask value={field.originalValue} type="npi" />
            ) : (
              field.originalValue
            )}
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Validated Value
          </label>
          <div className="text-sm text-gray-900 font-mono">
            {field.fieldName === 'phone_primary' ? (
              <PrivacyMask value={field.validatedValue} type="phone" />
            ) : field.fieldName === 'email' ? (
              <PrivacyMask value={field.validatedValue} type="email" />
            ) : field.fieldName === 'npi_number' ? (
              <PrivacyMask value={field.validatedValue} type="npi" />
            ) : (
              field.validatedValue
            )}
          </div>
        </div>
      </div>

      <div className="mb-3">
        <ConfidenceProgress confidence={field.confidence} />
      </div>

      {showDetails && (
        <div className="border-t border-gray-200 pt-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Validation Source
              </label>
              <SourceChip source={field.validationSource} size="sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Validated At
              </label>
              <div className="text-sm text-gray-900">
                {formatDate(field.validationTimestamp, 'long')}
              </div>
            </div>
          </div>

          {field.issues.length > 0 && (
            <div className="mt-3">
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Issues
              </label>
              <ul className="text-sm text-error-600">
                {field.issues.map((issue: string, index: number) => (
                  <li key={index} className="flex items-center gap-2">
                    <ExclamationTriangleIcon className="h-4 w-4" />
                    {issue}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {field.suggestions.length > 0 && (
            <div className="mt-3">
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Suggestions
              </label>
              <ul className="text-sm text-gray-600">
                {field.suggestions.map((suggestion: string, index: number) => (
                  <li key={index} className="flex items-center gap-2">
                    <CheckCircleIcon className="h-4 w-4 text-success-500" />
                    {suggestion}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function ProviderDetailPage() {
  const router = useRouter()
  const [showReviewModal, setShowReviewModal] = useState(false)

  // In a real app, this would get the provider ID from the URL params
  const providerId = 'provider_123'

  const { data: provider, isLoading, error } = useQuery(
    ['provider', providerId],
    async () => {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      return mockProviderDetail
    },
    {
      staleTime: 5 * 60 * 1000,
    }
  )

  const handleReviewAction = async (action: 'accept' | 'reject' | 'request_verification', note?: string) => {
    // Implement review action logic
    console.log('Review action:', action, provider?.id, note)
    setShowReviewModal(false)
  }

  const handleRevalidate = async () => {
    // Implement revalidation logic
    console.log('Revalidating provider:', provider?.id)
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="loading-spinner mx-auto mb-4" />
          <p className="text-gray-600">Loading provider details...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-900 font-medium mb-2">Error loading provider</p>
          <p className="text-gray-600">Please try refreshing the page</p>
        </div>
      </div>
    )
  }

  if (!provider) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-900 font-medium mb-2">Provider not found</p>
          <button
            onClick={() => router.back()}
            className="btn btn-primary"
          >
            Go Back
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => router.back()}
            className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeftIcon className="h-5 w-5 mr-2" />
            Back to Providers
          </button>
          
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                {provider.givenName} {provider.familyName}
              </h1>
              <p className="mt-2 text-gray-600">
                Provider ID: {provider.providerId} • NPI: {provider.npiNumber}
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleRevalidate}
                className="btn btn-outline"
              >
                <ArrowPathIcon className="h-4 w-4 mr-2" />
                Re-validate
              </button>
              <button className="btn btn-outline">
                <PencilIcon className="h-4 w-4 mr-2" />
                Edit
              </button>
              <button className="btn btn-outline">
                <PrinterIcon className="h-4 w-4 mr-2" />
                Print
              </button>
            </div>
          </div>
        </div>

        {/* Provider Summary */}
        <div className="bg-white shadow rounded-lg p-6 mb-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-500 mb-1">
                    Practice Name
                  </label>
                  <div className="text-lg font-medium text-gray-900">
                    {provider.practiceName}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500 mb-1">
                    Specialty
                  </label>
                  <div className="text-lg font-medium text-gray-900">
                    {provider.primaryTaxonomy}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500 mb-1">
                    Phone
                  </label>
                  <div className="text-lg font-medium text-gray-900">
                    <PrivacyMask value={provider.phonePrimary} type="phone" />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500 mb-1">
                    Email
                  </label>
                  <div className="text-lg font-medium text-gray-900">
                    <PrivacyMask value={provider.email} type="email" />
                  </div>
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-500 mb-1">
                    Address
                  </label>
                  <div className="text-lg font-medium text-gray-900">
                    {provider.addressStreet}, {provider.addressCity}, {provider.addressState} {provider.addressZip}
                  </div>
                </div>
              </div>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-500 mb-1">
                  Overall Confidence
                </label>
                <ConfidenceMeter 
                  confidence={provider.overallConfidence}
                  showPercentage={true}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-500 mb-1">
                  Validation Status
                </label>
                <div className="flex items-center gap-2">
                  <span className={`badge ${
                    provider.validationStatus === 'valid' ? 'badge-success' :
                    provider.validationStatus === 'warning' ? 'badge-warning' :
                    'badge-error'
                  }`}>
                    {provider.validationStatus}
                  </span>
                  {provider.flags.length > 0 && (
                    <span className="text-sm text-warning-600">
                      {provider.flags.length} flag{provider.flags.length > 1 ? 's' : ''}
                    </span>
                  )}
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-500 mb-1">
                  License Status
                </label>
                <div className="flex items-center gap-2">
                  <span className={`badge ${
                    provider.licenseStatus === 'ACTIVE' ? 'badge-success' :
                    provider.licenseStatus === 'INACTIVE' ? 'badge-warning' :
                    'badge-error'
                  }`}>
                    {provider.licenseStatus}
                  </span>
                  <span className="text-sm text-gray-600">
                    {provider.licenseNumber} ({provider.licenseState})
                  </span>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-500 mb-1">
                  Last Validated
                </label>
                <div className="text-sm text-gray-900">
                  {formatDate(provider.lastValidatedAt, 'long')}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Field Analysis */}
        <div className="bg-white shadow rounded-lg p-6 mb-8">
          <h3 className="text-lg font-medium text-gray-900 mb-6">
            Field Analysis
          </h3>
          <div className="space-y-4">
            {provider.fieldAnalyses.map((field, index) => (
              <FieldAnalysis key={index} field={field} />
            ))}
          </div>
        </div>

        {/* Sources */}
        <div className="bg-white shadow rounded-lg p-6 mb-8">
          <h3 className="text-lg font-medium text-gray-900 mb-6">
            Validation Sources
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-3">
                Source Comparison
              </h4>
              <SourceComparison sources={provider.sources} />
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-3">
                Source Reliability
              </h4>
              <div className="space-y-2">
                {provider.sources.map((source, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <SourceChip source={source.source} size="sm" />
                    <SourceReliability source={source.source} />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Timeline */}
        <div className="bg-white shadow rounded-lg p-6 mb-8">
          <h3 className="text-lg font-medium text-gray-900 mb-6">
            Validation Timeline
          </h3>
          <Timeline events={provider.timeline} />
        </div>

        {/* Recommendations */}
        {provider.recommendations.length > 0 && (
          <div className="bg-white shadow rounded-lg p-6 mb-8">
            <h3 className="text-lg font-medium text-gray-900 mb-6">
              Recommendations
            </h3>
            <div className="space-y-3">
              {provider.recommendations.map((recommendation, index) => (
                <div key={index} className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg">
                  <CheckCircleIcon className="h-5 w-5 text-blue-600 mt-0.5" />
                  <div className="text-sm text-blue-800">
                    {recommendation}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-center gap-4">
          <button
            onClick={() => setShowReviewModal(true)}
            className="btn btn-primary"
          >
            <CheckCircleIcon className="h-4 w-4 mr-2" />
            Review Provider
          </button>
          <button className="btn btn-outline">
            <DocumentTextIcon className="h-4 w-4 mr-2" />
            Generate Report
          </button>
        </div>

        {/* Manual Review Modal */}
        {showReviewModal && (
          <ManualReviewModal
            isOpen={showReviewModal}
            onClose={() => setShowReviewModal(false)}
            provider={{
              id: provider.id,
              name: `${provider.givenName} ${provider.familyName}`,
              npi: provider.npiNumber,
              overallConfidence: provider.overallConfidence,
              validationStatus: provider.validationStatus,
              flags: provider.flags,
            }}
            onAction={handleReviewAction}
          />
        )}
      </div>
    </div>
  )
}
