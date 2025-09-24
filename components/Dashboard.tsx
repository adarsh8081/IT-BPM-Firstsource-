'use client'

import { useState, useEffect } from 'react'
import { 
  UsersIcon, 
  CheckCircleIcon, 
  ExclamationTriangleIcon,
  ClockIcon 
} from '@heroicons/react/24/outline'

interface DashboardStats {
  totalProviders: number
  validatedProviders: number
  pendingValidation: number
  validationErrors: number
  recentValidations: Array<{
    id: string
    providerName: string
    status: 'valid' | 'invalid' | 'pending' | 'warning'
    timestamp: string
  }>
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    totalProviders: 0,
    validatedProviders: 0,
    pendingValidation: 0,
    validationErrors: 0,
    recentValidations: []
  })

  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Simulate API call
    setTimeout(() => {
      setStats({
        totalProviders: 200,
        validatedProviders: 156,
        pendingValidation: 32,
        validationErrors: 12,
        recentValidations: [
          {
            id: '1',
            providerName: 'Dr. Sarah Johnson',
            status: 'valid',
            timestamp: '2024-01-15T10:30:00Z'
          },
          {
            id: '2',
            providerName: 'Dr. Michael Chen',
            status: 'warning',
            timestamp: '2024-01-15T10:25:00Z'
          },
          {
            id: '3',
            providerName: 'Dr. Emily Rodriguez',
            status: 'invalid',
            timestamp: '2024-01-15T10:20:00Z'
          },
          {
            id: '4',
            providerName: 'Dr. David Thompson',
            status: 'pending',
            timestamp: '2024-01-15T10:15:00Z'
          }
        ]
      })
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

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString()
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
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <UsersIcon className="h-8 w-8 text-primary-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Total Providers</p>
              <p className="text-2xl font-semibold text-gray-900">
                {stats.totalProviders.toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <CheckCircleIcon className="h-8 w-8 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Validated</p>
              <p className="text-2xl font-semibold text-gray-900">
                {stats.validatedProviders.toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <ClockIcon className="h-8 w-8 text-yellow-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Pending</p>
              <p className="text-2xl font-semibold text-gray-900">
                {stats.pendingValidation.toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <ExclamationTriangleIcon className="h-8 w-8 text-red-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Errors</p>
              <p className="text-2xl font-semibold text-gray-900">
                {stats.validationErrors.toLocaleString()}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Validations */}
      <div className="card">
        <h3 className="text-lg font-medium text-gray-900 mb-4">
          Recent Validations
        </h3>
        <div className="overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="table-header">Provider</th>
                <th className="table-header">Status</th>
                <th className="table-header">Timestamp</th>
                <th className="table-header">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {stats.recentValidations.map((validation) => (
                <tr key={validation.id}>
                  <td className="table-cell font-medium">
                    {validation.providerName}
                  </td>
                  <td className="table-cell">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(validation.status)}`}>
                      {validation.status.charAt(0).toUpperCase() + validation.status.slice(1)}
                    </span>
                  </td>
                  <td className="table-cell text-gray-500">
                    {formatTimestamp(validation.timestamp)}
                  </td>
                  <td className="table-cell">
                    <button className="text-primary-600 hover:text-primary-900 text-sm font-medium">
                      View Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card">
        <h3 className="text-lg font-medium text-gray-900 mb-4">
          Quick Actions
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button className="btn-primary">
            Start New Validation
          </button>
          <button className="btn-secondary">
            Export Provider Data
          </button>
          <button className="btn-secondary">
            View Validation Reports
          </button>
        </div>
      </div>
    </div>
  )
}
