'use client'

import { useState, useEffect } from 'react'
import { 
  PlayIcon,
  PauseIcon,
  StopIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon
} from '@heroicons/react/24/outline'

interface ValidationJob {
  id: string
  providerId: string
  providerName: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  priority: 'low' | 'medium' | 'high'
  createdAt: string
  startedAt?: string
  completedAt?: string
  progress: number
  errors?: string[]
  results?: {
    npiValid: boolean
    addressValid: boolean
    licenseValid: boolean
    overallScore: number
  }
}

export default function ValidationQueue() {
  const [jobs, setJobs] = useState<ValidationJob[]>([])
  const [loading, setLoading] = useState(true)
  const [queueStatus, setQueueStatus] = useState<'running' | 'paused' | 'stopped'>('stopped')

  useEffect(() => {
    // Simulate API call
    setTimeout(() => {
      const mockJobs: ValidationJob[] = [
        {
          id: 'job-1',
          providerId: 'provider-1',
          providerName: 'Dr. Sarah Johnson',
          status: 'running',
          priority: 'high',
          createdAt: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
          startedAt: new Date(Date.now() - 4 * 60 * 1000).toISOString(),
          progress: 65,
          results: {
            npiValid: true,
            addressValid: true,
            licenseValid: false,
            overallScore: 75
          }
        },
        {
          id: 'job-2',
          providerId: 'provider-2',
          providerName: 'Dr. Michael Chen',
          status: 'pending',
          priority: 'medium',
          createdAt: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
          progress: 0
        },
        {
          id: 'job-3',
          providerId: 'provider-3',
          providerName: 'Dr. Emily Rodriguez',
          status: 'completed',
          priority: 'low',
          createdAt: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
          startedAt: new Date(Date.now() - 25 * 60 * 1000).toISOString(),
          completedAt: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
          progress: 100,
          results: {
            npiValid: true,
            addressValid: true,
            licenseValid: true,
            overallScore: 95
          }
        },
        {
          id: 'job-4',
          providerId: 'provider-4',
          providerName: 'Dr. David Thompson',
          status: 'failed',
          priority: 'high',
          createdAt: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
          startedAt: new Date(Date.now() - 40 * 60 * 1000).toISOString(),
          completedAt: new Date(Date.now() - 35 * 60 * 1000).toISOString(),
          progress: 30,
          errors: ['NPI validation failed', 'Address not found in Google Places']
        }
      ]
      setJobs(mockJobs)
      setLoading(false)
    }, 1000)
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-100'
      case 'running':
        return 'text-blue-600 bg-blue-100'
      case 'failed':
        return 'text-red-600 bg-red-100'
      case 'pending':
        return 'text-yellow-600 bg-yellow-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'text-red-600 bg-red-100'
      case 'medium':
        return 'text-yellow-600 bg-yellow-100'
      case 'low':
        return 'text-green-600 bg-green-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  const formatDuration = (startTime: string, endTime?: string) => {
    const start = new Date(startTime)
    const end = endTime ? new Date(endTime) : new Date()
    const diffMs = end.getTime() - start.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffSecs = Math.floor((diffMs % 60000) / 1000)
    return `${diffMins}m ${diffSecs}s`
  }

  const handleQueueControl = (action: 'start' | 'pause' | 'stop') => {
    setQueueStatus(action === 'start' ? 'running' : action)
    // Here you would make API calls to control the queue
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
      {/* Queue Controls */}
      <div className="card">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Validation Queue</h2>
            <p className="text-gray-600 mt-1">
              Status: <span className={`font-medium ${
                queueStatus === 'running' ? 'text-green-600' : 
                queueStatus === 'paused' ? 'text-yellow-600' : 'text-gray-600'
              }`}>
                {queueStatus.charAt(0).toUpperCase() + queueStatus.slice(1)}
              </span>
            </p>
          </div>
          <div className="flex space-x-3">
            {queueStatus === 'stopped' || queueStatus === 'paused' ? (
              <button 
                onClick={() => handleQueueControl('start')}
                className="btn-primary flex items-center"
              >
                <PlayIcon className="h-4 w-4 mr-2" />
                Start Queue
              </button>
            ) : (
              <button 
                onClick={() => handleQueueControl('pause')}
                className="btn-secondary flex items-center"
              >
                <PauseIcon className="h-4 w-4 mr-2" />
                Pause
              </button>
            )}
            <button 
              onClick={() => handleQueueControl('stop')}
              className="btn-secondary flex items-center"
            >
              <StopIcon className="h-4 w-4 mr-2" />
              Stop
            </button>
          </div>
        </div>
      </div>

      {/* Queue Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="card">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <ClockIcon className="h-8 w-8 text-yellow-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Pending</p>
              <p className="text-2xl font-semibold text-gray-900">
                {jobs.filter(job => job.status === 'pending').length}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <PlayIcon className="h-8 w-8 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Running</p>
              <p className="text-2xl font-semibold text-gray-900">
                {jobs.filter(job => job.status === 'running').length}
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
              <p className="text-sm font-medium text-gray-500">Completed</p>
              <p className="text-2xl font-semibold text-gray-900">
                {jobs.filter(job => job.status === 'completed').length}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <XCircleIcon className="h-8 w-8 text-red-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Failed</p>
              <p className="text-2xl font-semibold text-gray-900">
                {jobs.filter(job => job.status === 'failed').length}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Jobs List */}
      <div className="card">
        <h3 className="text-lg font-medium text-gray-900 mb-4">
          Validation Jobs
        </h3>
        <div className="overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="table-header">Provider</th>
                <th className="table-header">Status</th>
                <th className="table-header">Priority</th>
                <th className="table-header">Progress</th>
                <th className="table-header">Duration</th>
                <th className="table-header">Created</th>
                <th className="table-header">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {jobs.map((job) => (
                <tr key={job.id} className="hover:bg-gray-50">
                  <td className="table-cell font-medium">
                    {job.providerName}
                  </td>
                  <td className="table-cell">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(job.status)}`}>
                      {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                    </span>
                  </td>
                  <td className="table-cell">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getPriorityColor(job.priority)}`}>
                      {job.priority.charAt(0).toUpperCase() + job.priority.slice(1)}
                    </span>
                  </td>
                  <td className="table-cell">
                    <div className="flex items-center">
                      <div className="w-20 bg-gray-200 rounded-full h-2 mr-2">
                        <div 
                          className="bg-primary-600 h-2 rounded-full transition-all duration-300" 
                          style={{ width: `${job.progress}%` }}
                        ></div>
                      </div>
                      <span className="text-sm text-gray-600">{job.progress}%</span>
                    </div>
                  </td>
                  <td className="table-cell text-gray-500">
                    {job.startedAt ? formatDuration(job.startedAt, job.completedAt) : '-'}
                  </td>
                  <td className="table-cell text-gray-500">
                    {new Date(job.createdAt).toLocaleString()}
                  </td>
                  <td className="table-cell">
                    <div className="flex space-x-2">
                      <button className="text-primary-600 hover:text-primary-900 text-sm font-medium">
                        View
                      </button>
                      {job.status === 'pending' && (
                        <button className="text-primary-600 hover:text-primary-900 text-sm font-medium">
                          Cancel
                        </button>
                      )}
                      {job.status === 'failed' && (
                        <button className="text-primary-600 hover:text-primary-900 text-sm font-medium">
                          Retry
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Job Details Modal Placeholder */}
      {jobs.some(job => job.errors && job.errors.length > 0) && (
        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            Recent Errors
          </h3>
          <div className="space-y-3">
            {jobs.filter(job => job.errors && job.errors.length > 0).map((job) => (
              <div key={job.id} className="bg-red-50 border border-red-200 rounded-lg p-4">
                <h4 className="font-medium text-red-800">{job.providerName}</h4>
                <ul className="mt-2 text-sm text-red-700">
                  {job.errors?.map((error, index) => (
                    <li key={index}>• {error}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
