'use client'

import { useState, useMemo, useEffect } from 'react'
import { useQuery } from 'react-query'
import { 
  MagnifyingGlassIcon, 
  FunnelIcon, 
  ArrowDownTrayIcon,
  PlusIcon,
  EyeIcon,
  PencilIcon
} from '@heroicons/react/24/outline'
import { formatNumber, formatDate } from '@/lib/utils'
import { ConfidenceBadge } from '@/components/ui/ConfidenceBadge'
import { SourceChip } from '@/components/ui/SourceChip'
import { PrivacyMask } from '@/components/ui/PrivacyMask'
import { BulkActionToolbar } from '@/components/ui/BulkActionToolbar'
import { ManualReviewModal } from '@/components/ui/ManualReviewModal'

// Mock data - in real app, this would come from API
const mockProviders = Array.from({ length: 200 }, (_, i) => ({
  id: `provider_${i + 1}`,
  providerId: `PROV${String(i + 1).padStart(6, '0')}`,
  givenName: ['Dr. John', 'Dr. Sarah', 'Dr. Michael', 'Dr. Emily', 'Dr. David'][i % 5],
  familyName: ['Smith', 'Johnson', 'Brown', 'Davis', 'Wilson'][i % 5],
  npiNumber: `${1000000000 + i}`,
  phonePrimary: `+1-555-${String(Math.floor(Math.random() * 900) + 100)}-${String(Math.floor(Math.random() * 9000) + 1000)}`,
  email: `provider${i + 1}@example.com`,
  addressStreet: `${100 + i} Main Street`,
  addressCity: ['San Francisco', 'Los Angeles', 'New York', 'Chicago', 'Houston'][i % 5],
  addressState: ['CA', 'NY', 'TX', 'IL', 'FL'][i % 5],
  licenseNumber: `LIC${String(i + 1).padStart(6, '0')}`,
  licenseState: ['CA', 'NY', 'TX', 'IL', 'FL'][i % 5],
  licenseStatus: ['ACTIVE', 'INACTIVE', 'SUSPENDED'][i % 3],
  primaryTaxonomy: ['Internal Medicine', 'Cardiology', 'Pediatrics', 'Surgery', 'Dermatology'][i % 5],
  practiceName: `Medical Group ${i + 1}`,
  overallConfidence: Math.random() * 0.4 + 0.6, // 0.6 to 1.0
  validationStatus: ['valid', 'warning', 'invalid'][i % 3],
  flags: i % 7 === 0 ? ['MISSING_NPI', 'LOW_CONFIDENCE'] : i % 11 === 0 ? ['INVALID_PHONE'] : [],
  lastValidatedAt: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString(),
  createdAt: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
  sources: [
    { source: 'npi', confidence: 0.9 + Math.random() * 0.1 },
    { source: 'google_places', confidence: 0.8 + Math.random() * 0.2 },
    { source: 'state_board', confidence: 0.85 + Math.random() * 0.15 },
  ]
}))

interface FilterState {
  search: string
  confidenceRange: [number, number]
  validationStatus: string[]
  licenseStatus: string[]
  flags: string[]
  sources: string[]
  dateRange: { start: string; end: string }
}

interface SortState {
  field: string
  direction: 'asc' | 'desc'
}

export function ProvidersPage() {
  const [selectedProviders, setSelectedProviders] = useState<Set<string>>(new Set())
  const [showFilters, setShowFilters] = useState(false)
  const [showReviewModal, setShowReviewModal] = useState(false)
  const [reviewProvider, setReviewProvider] = useState<any>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  
  const [filters, setFilters] = useState<FilterState>({
    search: '',
    confidenceRange: [0, 1],
    validationStatus: [],
    licenseStatus: [],
    flags: [],
    sources: [],
    dateRange: { start: '', end: '' }
  })
  
  const [sort, setSort] = useState<SortState>({
    field: 'lastValidatedAt',
    direction: 'desc'
  })

  const { data: providers, isLoading, error } = useQuery(
    ['providers', filters, sort, currentPage, pageSize],
    async () => {
      // Simulate API call with filtering, sorting, and pagination
      await new Promise(resolve => setTimeout(resolve, 500))
      
      let filtered = [...mockProviders]
      
      // Apply search filter
      if (filters.search) {
        const searchLower = filters.search.toLowerCase()
        filtered = filtered.filter(provider =>
          provider.givenName.toLowerCase().includes(searchLower) ||
          provider.familyName.toLowerCase().includes(searchLower) ||
          provider.npiNumber.includes(searchLower) ||
          provider.email.toLowerCase().includes(searchLower) ||
          provider.practiceName.toLowerCase().includes(searchLower)
        )
      }
      
      // Apply confidence range filter
      filtered = filtered.filter(provider =>
        provider.overallConfidence >= filters.confidenceRange[0] &&
        provider.overallConfidence <= filters.confidenceRange[1]
      )
      
      // Apply validation status filter
      if (filters.validationStatus.length > 0) {
        filtered = filtered.filter(provider =>
          filters.validationStatus.includes(provider.validationStatus)
        )
      }
      
      // Apply license status filter
      if (filters.licenseStatus.length > 0) {
        filtered = filtered.filter(provider =>
          filters.licenseStatus.includes(provider.licenseStatus)
        )
      }
      
      // Apply flags filter
      if (filters.flags.length > 0) {
        filtered = filtered.filter(provider =>
          filters.flags.some(flag => provider.flags.includes(flag))
        )
      }
      
      // Apply sources filter
      if (filters.sources.length > 0) {
        filtered = filtered.filter(provider =>
          filters.sources.some(source => 
            provider.sources.some(s => s.source === source)
          )
        )
      }
      
      // Apply sorting
      filtered.sort((a, b) => {
        const aValue = a[sort.field as keyof typeof a]
        const bValue = b[sort.field as keyof typeof b]
        
        if (typeof aValue === 'string' && typeof bValue === 'string') {
          return sort.direction === 'asc' 
            ? aValue.localeCompare(bValue)
            : bValue.localeCompare(aValue)
        }
        
        if (typeof aValue === 'number' && typeof bValue === 'number') {
          return sort.direction === 'asc' ? aValue - bValue : bValue - aValue
        }
        
        return 0
      })
      
      // Apply pagination
      const startIndex = (currentPage - 1) * pageSize
      const endIndex = startIndex + pageSize
      const paginatedData = filtered.slice(startIndex, endIndex)
      
      return {
        providers: paginatedData,
        totalCount: filtered.length,
        totalPages: Math.ceil(filtered.length / pageSize)
      }
    },
    {
      keepPreviousData: true,
      staleTime: 5 * 60 * 1000,
    }
  )

  const handleSelectProvider = (providerId: string) => {
    const newSelected = new Set(selectedProviders)
    if (newSelected.has(providerId)) {
      newSelected.delete(providerId)
    } else {
      newSelected.add(providerId)
    }
    setSelectedProviders(newSelected)
  }

  const handleSelectAll = () => {
    if (selectedProviders.size === providers?.providers.length) {
      setSelectedProviders(new Set())
    } else {
      setSelectedProviders(new Set(providers?.providers.map(p => p.id) || []))
    }
  }

  const handleBulkAccept = async () => {
    // Implement bulk accept logic
    console.log('Bulk accept:', Array.from(selectedProviders))
    setSelectedProviders(new Set())
  }

  const handleBulkReject = async () => {
    // Implement bulk reject logic
    console.log('Bulk reject:', Array.from(selectedProviders))
    setSelectedProviders(new Set())
  }

  const handleBulkRequestVerification = async () => {
    // Implement bulk request verification logic
    console.log('Bulk request verification:', Array.from(selectedProviders))
    setSelectedProviders(new Set())
  }

  const handleBulkExport = async (format: 'csv' | 'pdf') => {
    // Implement bulk export logic
    console.log('Bulk export:', format, Array.from(selectedProviders))
  }

  const handleReviewAction = async (action: 'accept' | 'reject' | 'request_verification', note?: string) => {
    // Implement review action logic
    console.log('Review action:', action, reviewProvider?.id, note)
    setShowReviewModal(false)
    setReviewProvider(null)
  }

  const handleSort = (field: string) => {
    setSort(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'asc' ? 'desc' : 'asc'
    }))
  }

  const clearFilters = () => {
    setFilters({
      search: '',
      confidenceRange: [0, 1],
      validationStatus: [],
      licenseStatus: [],
      flags: [],
      sources: [],
      dateRange: { start: '', end: '' }
    })
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="loading-spinner mx-auto mb-4" />
          <p className="text-gray-600">Loading providers...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-900 font-medium mb-2">Error loading providers</p>
          <p className="text-gray-600">Please try refreshing the page</p>
        </div>
      </div>
    )
  }

  const { providers: providerList, totalCount, totalPages } = providers!

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Providers</h1>
              <p className="mt-2 text-gray-600">
                Manage and review provider validation data
              </p>
            </div>
            <div className="flex gap-3">
              <button className="btn btn-outline">
                <ArrowDownTrayIcon className="h-4 w-4 mr-2" />
                Export
              </button>
              <button className="btn btn-primary">
                <PlusIcon className="h-4 w-4 mr-2" />
                Add Provider
              </button>
            </div>
          </div>
        </div>

        {/* Filters and Search */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">Filters</h3>
            <button
              type="button"
              className="btn btn-outline btn-sm"
              onClick={() => setShowFilters(!showFilters)}
            >
              <FunnelIcon className="h-4 w-4 mr-2" />
              {showFilters ? 'Hide' : 'Show'} Filters
            </button>
          </div>

          {/* Search */}
          <div className="relative mb-4">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              className="input pl-10"
              placeholder="Search providers by name, NPI, email, or practice..."
              value={filters.search}
              onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
            />
          </div>

          {showFilters && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Confidence Range */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Confidence Range
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.1"
                    className="input"
                    placeholder="Min"
                    value={filters.confidenceRange[0]}
                    onChange={(e) => setFilters(prev => ({
                      ...prev,
                      confidenceRange: [parseFloat(e.target.value) || 0, prev.confidenceRange[1]]
                    }))}
                  />
                  <span className="text-gray-500">-</span>
                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.1"
                    className="input"
                    placeholder="Max"
                    value={filters.confidenceRange[1]}
                    onChange={(e) => setFilters(prev => ({
                      ...prev,
                      confidenceRange: [prev.confidenceRange[0], parseFloat(e.target.value) || 1]
                    }))}
                  />
                </div>
              </div>

              {/* Validation Status */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Validation Status
                </label>
                <select
                  multiple
                  className="select"
                  value={filters.validationStatus}
                  onChange={(e) => setFilters(prev => ({
                    ...prev,
                    validationStatus: Array.from(e.target.selectedOptions, option => option.value)
                  }))}
                >
                  <option value="valid">Valid</option>
                  <option value="warning">Warning</option>
                  <option value="invalid">Invalid</option>
                </select>
              </div>

              {/* License Status */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  License Status
                </label>
                <select
                  multiple
                  className="select"
                  value={filters.licenseStatus}
                  onChange={(e) => setFilters(prev => ({
                    ...prev,
                    licenseStatus: Array.from(e.target.selectedOptions, option => option.value)
                  }))}
                >
                  <option value="ACTIVE">Active</option>
                  <option value="INACTIVE">Inactive</option>
                  <option value="SUSPENDED">Suspended</option>
                </select>
              </div>

              {/* Flags */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Flags
                </label>
                <select
                  multiple
                  className="select"
                  value={filters.flags}
                  onChange={(e) => setFilters(prev => ({
                    ...prev,
                    flags: Array.from(e.target.selectedOptions, option => option.value)
                  }))}
                >
                  <option value="MISSING_NPI">Missing NPI</option>
                  <option value="LOW_CONFIDENCE">Low Confidence</option>
                  <option value="INVALID_PHONE">Invalid Phone</option>
                  <option value="INVALID_EMAIL">Invalid Email</option>
                </select>
              </div>
            </div>
          )}

          <div className="flex justify-between items-center mt-4">
            <div className="text-sm text-gray-600">
              Showing {formatNumber(providerList.length)} of {formatNumber(totalCount)} providers
            </div>
            <button
              type="button"
              className="btn btn-outline btn-sm"
              onClick={clearFilters}
            >
              Clear Filters
            </button>
          </div>
        </div>

        {/* Bulk Actions */}
        <BulkActionToolbar
          selectedCount={selectedProviders.size}
          totalCount={totalCount}
          onSelectAll={handleSelectAll}
          onClearSelection={() => setSelectedProviders(new Set())}
          onBulkAction={(action, selectedIds) => {
            switch (action) {
              case 'accept':
                handleBulkAccept()
                break
              case 'reject':
                handleBulkReject()
                break
              case 'request_verification':
                handleBulkRequestVerification()
                break
              case 'export_csv':
                handleBulkExport('csv')
                break
              case 'export_pdf':
                handleBulkExport('pdf')
                break
              default:
                console.log('Bulk action:', action, selectedIds)
            }
          }}
          selectedIds={Array.from(selectedProviders)}
        />

        {/* Providers Table */}
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="table">
              <thead className="table-header">
                <tr>
                  <th className="table-header-cell">
                    <input
                      type="checkbox"
                      className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      checked={selectedProviders.size === providerList.length && providerList.length > 0}
                      onChange={handleSelectAll}
                      aria-label="Select all providers"
                    />
                  </th>
                  <th 
                    className="table-header-cell cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('givenName')}
                  >
                    Provider
                  </th>
                  <th className="table-header-cell">NPI</th>
                  <th className="table-header-cell">Contact</th>
                  <th className="table-header-cell">License</th>
                  <th 
                    className="table-header-cell cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('overallConfidence')}
                  >
                    Confidence
                  </th>
                  <th 
                    className="table-header-cell cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('validationStatus')}
                  >
                    Status
                  </th>
                  <th 
                    className="table-header-cell cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('lastValidatedAt')}
                  >
                    Last Validated
                  </th>
                  <th className="table-header-cell">Actions</th>
                </tr>
              </thead>
              <tbody className="table-body">
                {providerList.map((provider) => (
                  <tr key={provider.id} className="table-row">
                    <td className="table-cell">
                      <input
                        type="checkbox"
                        className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                        checked={selectedProviders.has(provider.id)}
                        onChange={() => handleSelectProvider(provider.id)}
                        aria-label={`Select ${provider.givenName} ${provider.familyName}`}
                      />
                    </td>
                    <td className="table-cell">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-10 w-10">
                          <div className="h-10 w-10 rounded-full bg-primary-100 flex items-center justify-center">
                            <span className="text-sm font-medium text-primary-700">
                              {provider.givenName[0]}{provider.familyName[0]}
                            </span>
                          </div>
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">
                            {provider.givenName} {provider.familyName}
                          </div>
                          <div className="text-sm text-gray-500">
                            {provider.practiceName}
                          </div>
                          <div className="text-sm text-gray-500">
                            {provider.primaryTaxonomy}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="table-cell">
                      <PrivacyMask
                        value={provider.npiNumber}
                        type="npi"
                        showLastDigits={4}
                      />
                    </td>
                    <td className="table-cell">
                      <div className="text-sm text-gray-900">
                        <PrivacyMask
                          value={provider.phonePrimary}
                          type="phone"
                          showLastDigits={4}
                        />
                      </div>
                      <div className="text-sm text-gray-500">
                        <PrivacyMask
                          value={provider.email}
                          type="email"
                          showDomain={true}
                        />
                      </div>
                    </td>
                    <td className="table-cell">
                      <div className="text-sm text-gray-900">
                        {provider.licenseNumber}
                      </div>
                      <div className="text-sm text-gray-500">
                        {provider.licenseState}
                      </div>
                      <div className="mt-1">
                        <span className={`badge ${
                          provider.licenseStatus === 'ACTIVE' ? 'badge-success' :
                          provider.licenseStatus === 'INACTIVE' ? 'badge-warning' :
                          'badge-error'
                        }`}>
                          {provider.licenseStatus}
                        </span>
                      </div>
                    </td>
                    <td className="table-cell">
                      <ConfidenceBadge confidence={provider.overallConfidence} />
                      {provider.flags.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {provider.flags.map((flag, index) => (
                            <span key={index} className="badge badge-warning text-xs">
                              {flag.replace('_', ' ')}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="table-cell">
                      <span className={`badge ${
                        provider.validationStatus === 'valid' ? 'badge-success' :
                        provider.validationStatus === 'warning' ? 'badge-warning' :
                        'badge-error'
                      }`}>
                        {provider.validationStatus}
                      </span>
                    </td>
                    <td className="table-cell">
                      <div className="text-sm text-gray-900">
                        {formatDate(provider.lastValidatedAt, 'short')}
                      </div>
                    </td>
                    <td className="table-cell">
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          className="btn btn-outline btn-sm"
                          onClick={() => {
                            setReviewProvider(provider)
                            setShowReviewModal(true)
                          }}
                          title="Review provider"
                        >
                          <EyeIcon className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          className="btn btn-outline btn-sm"
                          title="Edit provider"
                        >
                          <PencilIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between mt-6">
          <div className="text-sm text-gray-600">
            Showing {formatNumber((currentPage - 1) * pageSize + 1)} to{' '}
            {formatNumber(Math.min(currentPage * pageSize, totalCount))} of{' '}
            {formatNumber(totalCount)} results
          </div>
          
          <div className="flex items-center gap-2">
            <select
              className="select"
              value={pageSize}
              onChange={(e) => setPageSize(Number(e.target.value))}
            >
              <option value={10}>10 per page</option>
              <option value={25}>25 per page</option>
              <option value={50}>50 per page</option>
              <option value={100}>100 per page</option>
            </select>
            
            <div className="flex items-center gap-1">
              <button
                type="button"
                className="btn btn-outline btn-sm"
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
              >
                Previous
              </button>
              
              <span className="px-3 py-2 text-sm text-gray-700">
                Page {currentPage} of {totalPages}
              </span>
              
              <button
                type="button"
                className="btn btn-outline btn-sm"
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages}
              >
                Next
              </button>
            </div>
          </div>
        </div>

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
      </div>
    </div>
  )
}
