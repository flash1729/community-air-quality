'use client';

import { useState } from 'react';

interface AddSensorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface RegistrationResponse {
  sensor_id: string;
  token: string;
  ingestion_url: string;
  message: string;
}

export default function AddSensorModal({ isOpen, onClose, onSuccess }: AddSensorModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    hardware_id: '',
    hardware_model: '',
    contributor_name: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [registrationResult, setRegistrationResult] = useState<RegistrationResponse | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  if (!isOpen) return null;

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Sensor name is required';
    } else if (formData.name.trim().length > 160) {
      newErrors.name = 'Sensor name must be 160 characters or less';
    }

    if (!formData.hardware_id.trim()) {
      newErrors.hardware_id = 'Hardware ID is required';
    } else if (formData.hardware_id.trim().length > 80) {
      newErrors.hardware_id = 'Hardware ID must be 80 characters or less';
    }

    if (!formData.hardware_model.trim()) {
      newErrors.hardware_model = 'Hardware model is required';
    } else if (formData.hardware_model.trim().length > 120) {
      newErrors.hardware_model = 'Hardware model must be 120 characters or less';
    }

    if (!formData.contributor_name.trim()) {
      newErrors.contributor_name = 'Contributor name is required';
    } else if (formData.contributor_name.trim().length > 160) {
      newErrors.contributor_name = 'Contributor name must be 160 characters or less';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await fetch('/api/v1/community/sensors/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to register sensor');
      }

      const result: RegistrationResponse = await response.json();
      setRegistrationResult(result);
      onSuccess();
    } catch (error) {
      setApiError(error instanceof Error ? error.message : 'An unexpected error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopy = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  const handleClose = () => {
    setFormData({ name: '', hardware_id: '', hardware_model: '', contributor_name: '' });
    setErrors({});
    setApiError(null);
    setRegistrationResult(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b">
          <h2 className="text-2xl font-bold text-gray-900">
            {registrationResult ? 'Sensor Registered Successfully' : 'Add New Sensor'}
          </h2>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {!registrationResult ? (
            // Form View
            <form onSubmit={handleSubmit} className="space-y-5">
              <p className="text-gray-600 text-sm mb-4">
                Register your air quality monitoring device. The sensor will report its location along with measurements.
              </p>

              {apiError && (
                <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded">
                  {apiError}
                </div>
              )}

              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                  Sensor Name *
                </label>
                <input
                  type="text"
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors.name ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="My Home Sensor"
                  maxLength={160}
                />
                {errors.name && <p className="mt-1 text-sm text-red-600">{errors.name}</p>}
              </div>

              <div>
                <label htmlFor="hardware_id" className="block text-sm font-medium text-gray-700 mb-1">
                  Hardware ID *
                </label>
                <input
                  type="text"
                  id="hardware_id"
                  value={formData.hardware_id}
                  onChange={(e) => setFormData({ ...formData, hardware_id: e.target.value })}
                  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors.hardware_id ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="ESP32-ABC123"
                  maxLength={80}
                />
                {errors.hardware_id && <p className="mt-1 text-sm text-red-600">{errors.hardware_id}</p>}
              </div>

              <div>
                <label htmlFor="hardware_model" className="block text-sm font-medium text-gray-700 mb-1">
                  Hardware Model *
                </label>
                <input
                  type="text"
                  id="hardware_model"
                  value={formData.hardware_model}
                  onChange={(e) => setFormData({ ...formData, hardware_model: e.target.value })}
                  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors.hardware_model ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="ESP32 + PMS5003"
                  maxLength={120}
                />
                {errors.hardware_model && <p className="mt-1 text-sm text-red-600">{errors.hardware_model}</p>}
              </div>

              <div>
                <label htmlFor="contributor_name" className="block text-sm font-medium text-gray-700 mb-1">
                  Contributor Name *
                </label>
                <input
                  type="text"
                  id="contributor_name"
                  value={formData.contributor_name}
                  onChange={(e) => setFormData({ ...formData, contributor_name: e.target.value })}
                  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors.contributor_name ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="Your Name or Organization"
                  maxLength={160}
                />
                {errors.contributor_name && <p className="mt-1 text-sm text-red-600">{errors.contributor_name}</p>}
              </div>

              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={handleClose}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors"
                >
                  {isSubmitting ? 'Registering...' : 'Register Sensor'}
                </button>
              </div>
            </form>
          ) : (
            // Success View
            <div className="space-y-4">
              <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded flex items-start">
                <svg className="w-5 h-5 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <div>
                  <p className="font-semibold">Sensor registered successfully!</p>
                  <p className="text-sm mt-1">{registrationResult.message}</p>
                </div>
              </div>

              <div className="bg-yellow-50 border border-yellow-200 text-yellow-900 px-4 py-3 rounded flex items-start">
                <svg className="w-5 h-5 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <div>
                  <p className="font-semibold">Store these credentials securely</p>
                  <p className="text-sm mt-1">The authentication token cannot be retrieved later. Copy it now and save it in a secure location.</p>
                </div>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Sensor ID</label>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 px-3 py-2 bg-gray-50 border border-gray-300 rounded font-mono text-sm">
                      {registrationResult.sensor_id}
                    </code>
                    <button
                      onClick={() => handleCopy(registrationResult.sensor_id, 'sensor_id')}
                      className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded transition-colors"
                      title="Copy to clipboard"
                    >
                      {copiedField === 'sensor_id' ? (
                        <span className="text-green-600 text-sm">✓</span>
                      ) : (
                        <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Authentication Token</label>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 px-3 py-2 bg-gray-50 border border-gray-300 rounded font-mono text-sm break-all">
                      {registrationResult.token}
                    </code>
                    <button
                      onClick={() => handleCopy(registrationResult.token, 'token')}
                      className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded transition-colors"
                      title="Copy to clipboard"
                    >
                      {copiedField === 'token' ? (
                        <span className="text-green-600 text-sm">✓</span>
                      ) : (
                        <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Ingestion Endpoint</label>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 px-3 py-2 bg-gray-50 border border-gray-300 rounded font-mono text-sm">
                      {registrationResult.ingestion_url}
                    </code>
                    <button
                      onClick={() => handleCopy(registrationResult.ingestion_url, 'url')}
                      className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded transition-colors"
                      title="Copy to clipboard"
                    >
                      {copiedField === 'url' ? (
                        <span className="text-green-600 text-sm">✓</span>
                      ) : (
                        <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>
              </div>

              <div className="flex justify-end pt-4">
                <button
                  onClick={handleClose}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                >
                  Done
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
