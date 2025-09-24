'use client'

import { useState } from 'react'
import { 
  CogIcon,
  KeyIcon,
  GlobeAltIcon,
  DocumentTextIcon
} from '@heroicons/react/24/outline'

interface ApiSettings {
  npiApiKey: string
  googlePlacesApiKey: string
  googleMapsApiKey: string
  npiRateLimit: number
  googleRateLimit: number
  stateBoardRateLimit: number
}

interface ValidationSettings {
  autoValidation: boolean
  validationInterval: number
  maxRetries: number
  timeoutSeconds: number
  enableNpiValidation: boolean
  enableAddressValidation: boolean
  enableLicenseValidation: boolean
}

export default function Settings() {
  const [activeTab, setActiveTab] = useState<'api' | 'validation' | 'notifications' | 'system'>('api')
  const [apiSettings, setApiSettings] = useState<ApiSettings>({
    npiApiKey: '••••••••••••••••',
    googlePlacesApiKey: '••••••••••••••••',
    googleMapsApiKey: '••••••••••••••••',
    npiRateLimit: 100,
    googleRateLimit: 1000,
    stateBoardRateLimit: 10
  })
  const [validationSettings, setValidationSettings] = useState<ValidationSettings>({
    autoValidation: true,
    validationInterval: 24,
    maxRetries: 3,
    timeoutSeconds: 30,
    enableNpiValidation: true,
    enableAddressValidation: true,
    enableLicenseValidation: true
  })

  const tabs = [
    { id: 'api', name: 'API Settings', icon: KeyIcon },
    { id: 'validation', name: 'Validation', icon: CogIcon },
    { id: 'notifications', name: 'Notifications', icon: GlobeAltIcon },
    { id: 'system', name: 'System', icon: DocumentTextIcon },
  ] as const

  const handleApiSettingChange = (key: keyof ApiSettings, value: string | number) => {
    setApiSettings(prev => ({ ...prev, [key]: value }))
  }

  const handleValidationSettingChange = (key: keyof ValidationSettings, value: boolean | number) => {
    setValidationSettings(prev => ({ ...prev, [key]: value }))
  }

  const handleSaveSettings = () => {
    // Here you would make API calls to save settings
    console.log('Saving settings...', { apiSettings, validationSettings })
    alert('Settings saved successfully!')
  }

  const renderApiSettings = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-4">API Configuration</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              NPI Registry API Key
            </label>
            <input
              type="password"
              value={apiSettings.npiApiKey}
              onChange={(e) => handleApiSettingChange('npiApiKey', e.target.value)}
              className="input-field"
              placeholder="Enter NPI API key"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Google Places API Key
            </label>
            <input
              type="password"
              value={apiSettings.googlePlacesApiKey}
              onChange={(e) => handleApiSettingChange('googlePlacesApiKey', e.target.value)}
              className="input-field"
              placeholder="Enter Google Places API key"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Google Maps API Key
            </label>
            <input
              type="password"
              value={apiSettings.googleMapsApiKey}
              onChange={(e) => handleApiSettingChange('googleMapsApiKey', e.target.value)}
              className="input-field"
              placeholder="Enter Google Maps API key"
            />
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-4">Rate Limits</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              NPI API Rate Limit (requests/hour)
            </label>
            <input
              type="number"
              value={apiSettings.npiRateLimit}
              onChange={(e) => handleApiSettingChange('npiRateLimit', parseInt(e.target.value))}
              className="input-field"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Google API Rate Limit (requests/day)
            </label>
            <input
              type="number"
              value={apiSettings.googleRateLimit}
              onChange={(e) => handleApiSettingChange('googleRateLimit', parseInt(e.target.value))}
              className="input-field"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              State Board Rate Limit (requests/hour)
            </label>
            <input
              type="number"
              value={apiSettings.stateBoardRateLimit}
              onChange={(e) => handleApiSettingChange('stateBoardRateLimit', parseInt(e.target.value))}
              className="input-field"
            />
          </div>
        </div>
      </div>
    </div>
  )

  const renderValidationSettings = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-4">Validation Configuration</h3>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">
                Enable Auto Validation
              </label>
              <p className="text-sm text-gray-500">
                Automatically validate providers on a schedule
              </p>
            </div>
            <input
              type="checkbox"
              checked={validationSettings.autoValidation}
              onChange={(e) => handleValidationSettingChange('autoValidation', e.target.checked)}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">
                Enable NPI Validation
              </label>
              <p className="text-sm text-gray-500">
                Validate NPI numbers against the NPI Registry
              </p>
            </div>
            <input
              type="checkbox"
              checked={validationSettings.enableNpiValidation}
              onChange={(e) => handleValidationSettingChange('enableNpiValidation', e.target.checked)}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">
                Enable Address Validation
              </label>
              <p className="text-sm text-gray-500">
                Validate addresses using Google Places API
              </p>
            </div>
            <input
              type="checkbox"
              checked={validationSettings.enableAddressValidation}
              onChange={(e) => handleValidationSettingChange('enableAddressValidation', e.target.checked)}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">
                Enable License Validation
              </label>
              <p className="text-sm text-gray-500">
                Validate medical licenses against state boards
              </p>
            </div>
            <input
              type="checkbox"
              checked={validationSettings.enableLicenseValidation}
              onChange={(e) => handleValidationSettingChange('enableLicenseValidation', e.target.checked)}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-4">Validation Parameters</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Validation Interval (hours)
            </label>
            <input
              type="number"
              value={validationSettings.validationInterval}
              onChange={(e) => handleValidationSettingChange('validationInterval', parseInt(e.target.value))}
              className="input-field"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Max Retries
            </label>
            <input
              type="number"
              value={validationSettings.maxRetries}
              onChange={(e) => handleValidationSettingChange('maxRetries', parseInt(e.target.value))}
              className="input-field"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Timeout (seconds)
            </label>
            <input
              type="number"
              value={validationSettings.timeoutSeconds}
              onChange={(e) => handleValidationSettingChange('timeoutSeconds', parseInt(e.target.value))}
              className="input-field"
            />
          </div>
        </div>
      </div>
    </div>
  )

  const renderNotifications = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-4">Notification Settings</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">
                Email Notifications
              </label>
              <p className="text-sm text-gray-500">
                Receive email notifications for validation results
              </p>
            </div>
            <input
              type="checkbox"
              defaultChecked
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">
                Slack Notifications
              </label>
              <p className="text-sm text-gray-500">
                Send notifications to Slack channel
              </p>
            </div>
            <input
              type="checkbox"
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700">
                Dashboard Alerts
              </label>
              <p className="text-sm text-gray-500">
                Show alerts in the dashboard
              </p>
            </div>
            <input
              type="checkbox"
              defaultChecked
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
          </div>
        </div>
      </div>
    </div>
  )

  const renderSystem = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-4">System Information</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="card">
            <h4 className="font-medium text-gray-900 mb-2">Database</h4>
            <div className="space-y-2 text-sm text-gray-600">
              <div>Status: <span className="text-green-600 font-medium">Connected</span></div>
              <div>Type: PostgreSQL</div>
              <div>Version: 15.4</div>
              <div>Records: 200 providers</div>
            </div>
          </div>

          <div className="card">
            <h4 className="font-medium text-gray-900 mb-2">Queue System</h4>
            <div className="space-y-2 text-sm text-gray-600">
              <div>Status: <span className="text-green-600 font-medium">Active</span></div>
              <div>Type: Redis + RQ</div>
              <div>Workers: 3 active</div>
              <div>Jobs: 5 pending</div>
            </div>
          </div>

          <div className="card">
            <h4 className="font-medium text-gray-900 mb-2">API Endpoints</h4>
            <div className="space-y-2 text-sm text-gray-600">
              <div>NPI Registry: <span className="text-green-600 font-medium">Connected</span></div>
              <div>Google Places: <span className="text-green-600 font-medium">Connected</span></div>
              <div>State Boards: <span className="text-yellow-600 font-medium">Limited</span></div>
            </div>
          </div>

          <div className="card">
            <h4 className="font-medium text-gray-900 mb-2">Performance</h4>
            <div className="space-y-2 text-sm text-gray-600">
              <div>Avg Response Time: 245ms</div>
              <div>Success Rate: 98.5%</div>
              <div>Uptime: 99.9%</div>
              <div>Last Restart: 2 days ago</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Settings</h2>
        <button onClick={handleSaveSettings} className="btn-primary">
          Save Changes
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center ${
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <tab.icon className="h-4 w-4 mr-2" />
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="card">
        {activeTab === 'api' && renderApiSettings()}
        {activeTab === 'validation' && renderValidationSettings()}
        {activeTab === 'notifications' && renderNotifications()}
        {activeTab === 'system' && renderSystem()}
      </div>
    </div>
  )
}
