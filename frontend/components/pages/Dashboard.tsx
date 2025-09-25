'use client'

import { useState, useEffect } from 'react'
import { useQuery } from 'react-query'
import { 
  ChartBarIcon, 
  UserGroupIcon, 
  CheckCircleIcon, 
  ExclamationTriangleIcon,
  ClockIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon
} from '@heroicons/react/24/outline'
import { formatNumber, formatPercentage, formatDate } from '@/lib/utils'
import { ConfidenceBadge } from '@/components/ui/ConfidenceBadge'
import { Timeline, CompactTimeline } from '@/components/ui/Timeline'

// Mock data - in real app, this would come from API
const mockDashboardData = {
  kpis: {
    totalProviders: 1247,
    validatedProviders: 1156,
    pendingReview: 91,
    overallAccuracy: 0.87,
    averageProcessingTime: 2.3,
    dailyValidations: 156,
  },
  trends: {
    totalProviders: { change: 12, trend: 'up' },
    validatedProviders: { change: 8, trend: 'up' },
    pendingReview: { change: -3, trend: 'down' },
    overallAccuracy: { change: 2.1, trend: 'up' },
    averageProcessingTime: { change: -0.4, trend: 'down' },
    dailyValidations: { change: 15, trend: 'up' },
  },
  recentRuns: [
    {
      id: '1',
      type: 'validation',
      title: 'Batch validation completed',
      description: 'Successfully validated 45 providers from CSV import',
      timestamp: '2024-01-15T10:30:00Z',
      status: 'success',
      source: 'batch_import',
      confidence: 0.89,
      user: 'System',
    },
    {
      id: '2',
      type: 'review',
      title: 'Manual review completed',
      description: 'Provider Dr. Sarah Johnson approved by reviewer',
      timestamp: '2024-01-15T09:15:00Z',
      status: 'success',
      source: 'manual_review',
      confidence: 0.95,
      user: 'John Doe',
    },
    {
      id: '3',
      type: 'validation',
      title: 'NPI validation failed',
      description: 'Unable to validate NPI for provider 1234567890',
      timestamp: '2024-01-15T08:45:00Z',
      status: 'error',
      source: 'npi_registry',
      confidence: 0.0,
      user: 'System',
    },
    {
      id: '4',
      type: 'update',
      title: 'Provider data updated',
      description: 'Address information updated for Dr. Michael Brown',
      timestamp: '2024-01-15T07:20:00Z',
      status: 'success',
      source: 'google_places',
      confidence: 0.92,
      user: 'System',
    },
  ],
  validationStats: {
    bySource: [
      { source: 'npi', count: 1156, accuracy: 0.94 },
      { source: 'google_places', count: 1089, accuracy: 0.89 },
      { source: 'state_board', count: 1023, accuracy: 0.91 },
      { source: 'hospital_website', count: 567, accuracy: 0.76 },
      { source: 'manual', count: 91, accuracy: 1.0 },
    ],
    byConfidence: [
      { range: 'High (80-100%)', count: 892, percentage: 71.5 },
      { range: 'Medium (60-79%)', count: 234, percentage: 18.8 },
      { range: 'Low (0-59%)', count: 121, percentage: 9.7 },
    ],
  },
}

interface KPICardProps {
  title: string
  value: string | number
  change?: number
  trend?: 'up' | 'down'
  icon: React.ComponentType<{ className?: string }>
  description?: string
  format?: 'number' | 'percentage' | 'time'
}

function KPICard({ title, value, change, trend, icon: Icon, description, format = 'number' }: KPICardProps) {
  const formatValue = (val: string | number) => {
    if (typeof val === 'string') return val
    
    switch (format) {
      case 'percentage':
        return formatPercentage(val)
      case 'time':
        return `${val}s`
      default:
        return formatNumber(val)
    }
  }

  return (
    <div className="bg-white overflow-hidden shadow rounded-lg">
      <div className="p-5">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <Icon className="h-6 w-6 text-gray-400" aria-hidden="true" />
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="text-sm font-medium text-gray-500 truncate">
                {title}
              </dt>
              <dd className="flex items-baseline">
                <div className="text-2xl font-semibold text-gray-900">
                  {formatValue(value)}
                </div>
                {change !== undefined && (
                  <div className={`ml-2 flex items-baseline text-sm font-semibold ${
                    trend === 'up' ? 'text-success-600' : 'text-error-600'
                  }`}>
                    {trend === 'up' ? (
                      <ArrowTrendingUpIcon className="self-center flex-shrink-0 h-4 w-4 text-success-500" />
                    ) : (
                      <ArrowTrendingDownIcon className="self-center flex-shrink-0 h-4 w-4 text-error-500" />
                    )}
                    <span className="sr-only">
                      {trend === 'up' ? 'Increased' : 'Decreased'} by
                    </span>
                    {Math.abs(change)}%
                  </div>
                )}
              </dd>
              {description && (
                <dd className="text-sm text-gray-600 mt-1">
                  {description}
                </dd>
              )}
            </dl>
          </div>
        </div>
      </div>
    </div>
  )
}

interface ValidationStatsProps {
  stats: typeof mockDashboardData.validationStats
}

function ValidationStats({ stats }: ValidationStatsProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Validation by Source */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">
          Validation by Source
        </h3>
        <div className="space-y-4">
          {stats.bySource.map((source) => (
            <div key={source.source} className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="text-sm font-medium text-gray-900 capitalize">
                  {source.source.replace('_', ' ')}
                </div>
                <div className="ml-2 text-sm text-gray-500">
                  ({formatNumber(source.count)})
                </div>
              </div>
              <div className="flex items-center gap-2">
                <ConfidenceBadge confidence={source.accuracy} size="sm" />
                <div className="text-sm text-gray-600">
                  {formatPercentage(source.accuracy)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Validation by Confidence */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">
          Validation by Confidence
        </h3>
        <div className="space-y-4">
          {stats.byConfidence.map((confidence) => (
            <div key={confidence.range} className="flex items-center justify-between">
              <div className="text-sm font-medium text-gray-900">
                {confidence.range}
              </div>
              <div className="flex items-center gap-2">
                <div className="w-24 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${confidence.percentage}%` }}
                  />
                </div>
                <div className="text-sm text-gray-600 min-w-[3rem] text-right">
                  {formatNumber(confidence.count)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function Dashboard() {
  const { data: dashboardData, isLoading, error } = useQuery(
    'dashboard',
    async () => {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      return mockDashboardData
    },
    {
      staleTime: 5 * 60 * 1000, // 5 minutes
      refetchInterval: 30 * 1000, // 30 seconds
    }
  )

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="loading-spinner mx-auto mb-4" />
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <ExclamationTriangleIcon className="h-12 w-12 text-error-500 mx-auto mb-4" />
          <p className="text-gray-900 font-medium mb-2">Error loading dashboard</p>
          <p className="text-gray-600">Please try refreshing the page</p>
        </div>
      </div>
    )
  }

  const { kpis, trends, recentRuns, validationStats } = dashboardData!

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Provider Validation Dashboard</h1>
          <p className="mt-2 text-gray-600">
            Monitor provider validation performance and system health
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          <KPICard
            title="Total Providers"
            value={kpis.totalProviders}
            change={trends.totalProviders.change}
            trend={trends.totalProviders.trend}
            icon={UserGroupIcon}
            description="Registered providers in system"
          />
          <KPICard
            title="Validated Providers"
            value={kpis.validatedProviders}
            change={trends.validatedProviders.change}
            trend={trends.validatedProviders.trend}
            icon={CheckCircleIcon}
            description="Successfully validated providers"
          />
          <KPICard
            title="Pending Review"
            value={kpis.pendingReview}
            change={trends.pendingReview.change}
            trend={trends.pendingReview.trend}
            icon={ClockIcon}
            description="Providers awaiting manual review"
          />
          <KPICard
            title="Overall Accuracy"
            value={kpis.overallAccuracy}
            change={trends.overallAccuracy.change}
            trend={trends.overallAccuracy.trend}
            icon={ChartBarIcon}
            format="percentage"
            description="Average validation accuracy"
          />
          <KPICard
            title="Avg Processing Time"
            value={kpis.averageProcessingTime}
            change={trends.averageProcessingTime.change}
            trend={trends.averageProcessingTime.trend}
            icon={ClockIcon}
            format="time"
            description="Average time per validation"
          />
          <KPICard
            title="Daily Validations"
            value={kpis.dailyValidations}
            change={trends.dailyValidations.change}
            trend={trends.dailyValidations.trend}
            icon={ArrowTrendingUpIcon}
            description="Validations completed today"
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Recent Activity Timeline */}
          <div className="lg:col-span-2">
            <div className="bg-white shadow rounded-lg p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-medium text-gray-900">
                  Recent Activity
                </h3>
                <button className="text-sm text-primary-600 hover:text-primary-700 font-medium">
                  View all activity
                </button>
              </div>
              <Timeline events={recentRuns} />
            </div>
          </div>

          {/* Quick Stats */}
          <div className="space-y-6">
            <div className="bg-white shadow rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Quick Stats
              </h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Validation Success Rate</span>
                  <span className="text-sm font-medium text-gray-900">
                    {formatPercentage(kpis.overallAccuracy)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Pending Reviews</span>
                  <span className="text-sm font-medium text-warning-600">
                    {formatNumber(kpis.pendingReview)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Avg Confidence</span>
                  <span className="text-sm font-medium text-gray-900">
                    {formatPercentage(kpis.overallAccuracy)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Last Updated</span>
                  <span className="text-sm font-medium text-gray-900">
                    {formatDate(new Date(), 'relative')}
                  </span>
                </div>
              </div>
            </div>

            {/* Recent Activity Summary */}
            <div className="bg-white shadow rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Recent Activity
              </h3>
              <CompactTimeline events={recentRuns.slice(0, 5)} />
            </div>
          </div>
        </div>

        {/* Validation Statistics */}
        <div className="mt-8">
          <ValidationStats stats={validationStats} />
        </div>

        {/* Action Buttons */}
        <div className="mt-8 flex justify-center gap-4">
          <button className="btn btn-primary">
            Start New Validation
          </button>
          <button className="btn btn-outline">
            Export Report
          </button>
          <button className="btn btn-outline">
            View All Providers
          </button>
        </div>
      </div>
    </div>
  )
}
