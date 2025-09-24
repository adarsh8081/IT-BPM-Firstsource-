'use client'

import { useState, useEffect } from 'react'
import { 
  MagnifyingGlassIcon,
  FunnelIcon,
  PlusIcon,
  DocumentArrowDownIcon
} from '@heroicons/react/24/outline'

interface Provider {
  id: string
  npi: string
  firstName: string
  lastName: string
  specialty: string
  organization: string
  location: string
  status: 'valid' | 'invalid' | 'pending' | 'warning'
  lastValidated: string
  validationScore: number
}

export default function ProviderList() {
  const [providers, setProviders] = useState<Provider[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [selectedProviders, setSelectedProviders] = useState<string[]>([])

  useEffect(() => {
    // Simulate API call
    setTimeout(() => {
      const mockProviders: Provider[] = Array.from({ length: 50 }, (_, i) => ({
        id: `provider-${i + 1}`,
        npi: `123456789${i.toString().padStart(2, '0')}`,
        firstName: ['Sarah', 'Michael', 'Emily', 'David', 'Lisa', 'John', 'Maria', 'Robert'][i % 8],
        lastName: ['Johnson', 'Chen', 'Rodriguez', 'Thompson', 'Williams', 'Brown', 'Davis', 'Wilson'][i % 8],
        specialty: ['Cardiology', 'Internal Medicine', 'Pediatrics', 'Surgery', 'Radiology', 'Neurology', 'Oncology', 'Dermatology'][i % 8],
        organization: ['City General Hospital', 'Regional Medical Center', 'University Hospital', 'Community Health Clinic'][i % 4],
        location: ['New York, NY', 'Los Angeles, CA', 'Chicago, IL', 'Houston, TX', 'Phoenix, AZ'][i % 5],
        status: ['valid', 'invalid', 'pending', 'warning'][i % 4] as Provider['status'],
        lastValidated: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
        validationScore: Math.floor(Math.random() * 100)
      }))
      setProviders(mockProviders)
      setLoading(false)
    }, 1000)
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'valid':
        return 'text-green-600 bg-green-100'
      case 'invalid':
        return 'text-red-600 bg-red-100'
      case 'warning':
        return 'text-orange-600 bg-orange-100'
      case 'pending':
        return 'text-yellow-600 bg-yellow-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  const filteredProviders = providers.filter(provider => {
    const matchesSearch = provider.firstName.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         provider.lastName.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         provider.npi.includes(searchTerm) ||
                         provider.specialty.toLowerCase().includes(searchTerm.toLowerCase())
    
    const matchesStatus = statusFilter === 'all' || provider.status === statusFilter
    
    return matchesSearch && matchesStatus
  })

  const handleSelectProvider = (providerId: string) => {
    setSelectedProviders(prev => 
      prev.includes(providerId) 
        ? prev.filter(id => id !== providerId)
        : [...prev, providerId]
    )
  }

  const handleSelectAll = () => {
    if (selectedProviders.length === filteredProviders.length) {
      setSelectedProviders([])
    } else {
      setSelectedProviders(filteredProviders.map(p => p.id))
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Provider Directory</h2>
        <div className="flex space-x-3">
          <button className="btn-secondary flex items-center">
            <DocumentArrowDownIcon className="h-4 w-4 mr-2" />
            Export
          </button>
          <button className="btn-primary flex items-center">
            <PlusIcon className="h-4 w-4 mr-2" />
            Add Provider
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <MagnifyingGlassIcon className="h-5 w-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search providers..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="input-field pl-10"
              />
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center">
              <FunnelIcon className="h-5 w-5 text-gray-400 mr-2" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="input-field"
              >
                <option value="all">All Status</option>
                <option value="valid">Valid</option>
                <option value="invalid">Invalid</option>
                <option value="pending">Pending</option>
                <option value="warning">Warning</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedProviders.length > 0 && (
        <div className="card bg-blue-50 border-blue-200">
          <div className="flex items-center justify-between">
            <span className="text-blue-800">
              {selectedProviders.length} provider(s) selected
            </span>
            <div className="flex space-x-2">
              <button className="btn-primary">Validate Selected</button>
              <button className="btn-secondary">Export Selected</button>
              <button className="btn-secondary">Update Status</button>
            </div>
          </div>
        </div>
      )}

      {/* Providers Table */}
      <div className="card">
        <div className="overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3">
                  <input
                    type="checkbox"
                    checked={selectedProviders.length === filteredProviders.length && filteredProviders.length > 0}
                    onChange={handleSelectAll}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                </th>
                <th className="table-header">Provider</th>
                <th className="table-header">NPI</th>
                <th className="table-header">Specialty</th>
                <th className="table-header">Organization</th>
                <th className="table-header">Location</th>
                <th className="table-header">Status</th>
                <th className="table-header">Score</th>
                <th className="table-header">Last Validated</th>
                <th className="table-header">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredProviders.map((provider) => (
                <tr key={provider.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <input
                      type="checkbox"
                      checked={selectedProviders.includes(provider.id)}
                      onChange={() => handleSelectProvider(provider.id)}
                      className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                  </td>
                  <td className="table-cell font-medium">
                    Dr. {provider.firstName} {provider.lastName}
                  </td>
                  <td className="table-cell font-mono text-sm">
                    {provider.npi}
                  </td>
                  <td className="table-cell">
                    {provider.specialty}
                  </td>
                  <td className="table-cell">
                    {provider.organization}
                  </td>
                  <td className="table-cell">
                    {provider.location}
                  </td>
                  <td className="table-cell">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(provider.status)}`}>
                      {provider.status.charAt(0).toUpperCase() + provider.status.slice(1)}
                    </span>
                  </td>
                  <td className="table-cell">
                    <div className="flex items-center">
                      <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                        <div 
                          className="bg-primary-600 h-2 rounded-full" 
                          style={{ width: `${provider.validationScore}%` }}
                        ></div>
                      </div>
                      <span className="text-sm text-gray-600">{provider.validationScore}%</span>
                    </div>
                  </td>
                  <td className="table-cell text-gray-500">
                    {new Date(provider.lastValidated).toLocaleDateString()}
                  </td>
                  <td className="table-cell">
                    <div className="flex space-x-2">
                      <button className="text-primary-600 hover:text-primary-900 text-sm font-medium">
                        View
                      </button>
                      <button className="text-primary-600 hover:text-primary-900 text-sm font-medium">
                        Edit
                      </button>
                      <button className="text-primary-600 hover:text-primary-900 text-sm font-medium">
                        Validate
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
          <div className="flex-1 flex justify-between sm:hidden">
            <button className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
              Previous
            </button>
            <button className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
              Next
            </button>
          </div>
          <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
            <div>
              <p className="text-sm text-gray-700">
                Showing <span className="font-medium">1</span> to <span className="font-medium">10</span> of{' '}
                <span className="font-medium">{filteredProviders.length}</span> results
              </p>
            </div>
            <div>
              <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                <button className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50">
                  Previous
                </button>
                <button className="relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium text-gray-700 hover:bg-gray-50">
                  1
                </button>
                <button className="relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium text-gray-700 hover:bg-gray-50">
                  2
                </button>
                <button className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50">
                  Next
                </button>
              </nav>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
