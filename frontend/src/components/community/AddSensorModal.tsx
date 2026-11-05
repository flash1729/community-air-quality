'use client';

import { Check, Copy, LoaderCircle, RadioTower, X } from 'lucide-react';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { createPortal } from 'react-dom';

import { Banner, SectionHeading } from '@/components/ui';

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

type FieldName = 'name' | 'hardware_id' | 'hardware_model' | 'contributor_name';

const FIELDS: { id: FieldName; label: string; placeholder: string; max: number }[] = [
  { id: 'name', label: 'Sensor name', placeholder: 'My Home Sensor', max: 160 },
  { id: 'hardware_id', label: 'Hardware ID', placeholder: 'ESP32-ABC123', max: 80 },
  { id: 'hardware_model', label: 'Hardware model', placeholder: 'ESP32 + PMS5003', max: 120 },
  { id: 'contributor_name', label: 'Contributor name', placeholder: 'Your name or organisation', max: 160 },
];

const EMPTY_FORM: Record<FieldName, string> = { name: '', hardware_id: '', hardware_model: '', contributor_name: '' };

export default function AddSensorModal({ isOpen, onClose, onSuccess }: AddSensorModalProps) {
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState<Partial<Record<FieldName, string>>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [registrationResult, setRegistrationResult] = useState<RegistrationResponse | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  const handleClose = () => {
    setFormData(EMPTY_FORM);
    setErrors({});
    setApiError(null);
    setRegistrationResult(null);
    onClose();
  };
  const closeRef = useRef(handleClose);
  closeRef.current = handleClose;

  // While open: Escape closes, the page behind is inert and does not scroll.
  useEffect(() => {
    if (!isOpen) return;
    const portalRoot = dialogRef.current?.closest('[data-modal-root]');
    const siblings = Array.from(document.body.children).filter(
      (el): el is HTMLElement => el instanceof HTMLElement && el !== portalRoot && !el.inert,
    );
    siblings.forEach((el) => (el.inert = true));
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    dialogRef.current?.querySelector<HTMLElement>('input, button')?.focus();

    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeRef.current();
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      siblings.forEach((el) => (el.inert = false));
      document.body.style.overflow = overflow;
    };
  }, [isOpen]);

  if (!isOpen || typeof document === 'undefined') return null;

  const validateForm = (): boolean => {
    const newErrors: Partial<Record<FieldName, string>> = {};
    for (const field of FIELDS) {
      const value = formData[field.id].trim();
      if (!value) newErrors[field.id] = `${field.label} is required`;
      else if (value.length > field.max) newErrors[field.id] = `${field.label} must be ${field.max} characters or less`;
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setApiError(null);
    if (!validateForm()) return;

    setIsSubmitting(true);
    try {
      const response = await fetch('/api/v1/community/sensors/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const detail = Array.isArray(errorData.detail) ? errorData.detail[0]?.msg : errorData.detail;
        throw new Error(typeof detail === 'string' && detail ? detail : 'Failed to register sensor');
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

  const credentials = registrationResult
    ? [
        { id: 'sensor_id', label: 'Sensor ID', value: registrationResult.sensor_id },
        { id: 'token', label: 'Authentication token', value: registrationResult.token },
        { id: 'url', label: 'Ingestion endpoint', value: registrationResult.ingestion_url },
      ]
    : [];

  return createPortal(
    <div data-modal-root className="fixed inset-0 z-[2000] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-paper/75 backdrop-blur-sm" aria-hidden="true" onClick={handleClose} />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-sensor-title"
        className="relative max-h-[90vh] w-full max-w-lg animate-pop overflow-y-auto rounded-3xl border border-line-strong bg-surface-solid p-5 shadow-pop sm:p-6"
      >
        <div className="flex items-start justify-between gap-4">
          <SectionHeading
            icon={<RadioTower size={17} />}
            title={<span id="add-sensor-title">{registrationResult ? 'Sensor registered' : 'Add sensor'}</span>}
            hint={
              registrationResult
                ? 'Use these credentials to connect your device.'
                : 'Your device reports its own location with every reading.'
            }
          />
          <button
            type="button"
            onClick={handleClose}
            aria-label="Close"
            className="grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-line bg-surface-2 text-muted transition duration-200 hover:border-line-strong hover:text-ink"
          >
            <X size={16} />
          </button>
        </div>

        {!registrationResult ? (
          <form onSubmit={handleSubmit} noValidate className="mt-6 space-y-4">
            {apiError && (
              <Banner tone="error" role="alert">
                {apiError}
              </Banner>
            )}

            {FIELDS.map((field) => (
              <div key={field.id}>
                <label htmlFor={field.id} className="mb-1.5 block text-xs font-medium text-muted">
                  {field.label}
                </label>
                <input
                  type="text"
                  id={field.id}
                  value={formData[field.id]}
                  onChange={(e) => setFormData({ ...formData, [field.id]: e.target.value })}
                  className={`field w-full py-2.5 placeholder:text-faint ${errors[field.id] ? 'border-danger' : ''}`}
                  placeholder={field.placeholder}
                  maxLength={field.max}
                  aria-invalid={Boolean(errors[field.id])}
                  aria-describedby={errors[field.id] ? `${field.id}-error` : undefined}
                />
                {errors[field.id] && (
                  <p id={`${field.id}-error`} className="mt-1.5 text-xs text-danger">
                    {errors[field.id]}
                  </p>
                )}
              </div>
            ))}

            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={handleClose} className="btn btn-ghost">
                Cancel
              </button>
              <button type="submit" disabled={isSubmitting} className="btn btn-primary">
                {isSubmitting && <LoaderCircle size={16} className="animate-spin" />}
                {isSubmitting ? 'Registering…' : 'Register sensor'}
              </button>
            </div>
          </form>
        ) : (
          <div className="mt-6 space-y-4">
            <Banner tone="info">{registrationResult.message}</Banner>
            <Banner tone="warn" role="alert">
              The authentication token is shown only once. Copy it now and store it securely.
            </Banner>

            <dl className="space-y-3">
              {credentials.map((item) => (
                <div key={item.id}>
                  <dt className="eyebrow mb-1.5">{item.label}</dt>
                  <dd className="flex items-start gap-2">
                    <code className="min-w-0 flex-1 break-all rounded-xl border border-line bg-surface-2 px-3 py-2.5 font-mono text-xs leading-5 text-ink">
                      {item.value}
                    </code>
                    <button
                      type="button"
                      onClick={() => handleCopy(item.value, item.id)}
                      aria-label={`Copy ${item.label.toLowerCase()}`}
                      title="Copy to clipboard"
                      className="btn btn-ghost h-[42px] w-[42px] shrink-0 px-0 py-0"
                    >
                      {copiedField === item.id ? <Check size={16} className="text-accent" /> : <Copy size={16} />}
                    </button>
                  </dd>
                </div>
              ))}
            </dl>

            <div className="flex justify-end pt-2">
              <button type="button" onClick={handleClose} className="btn btn-primary">
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}
