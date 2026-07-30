import type { ComplianceStatusValue, RiskLevel } from '../types'

const RISK_STYLES: Record<RiskLevel, string> = {
  unacceptable: 'bg-red-100 text-red-800 border-red-200',
  high: 'bg-orange-100 text-orange-800 border-orange-200',
  limited: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  minimal: 'bg-green-100 text-green-800 border-green-200',
}

const RISK_LABELS: Record<RiskLevel, string> = {
  unacceptable: 'Unacceptable risk',
  high: 'High risk',
  limited: 'Limited risk',
  minimal: 'Minimal risk',
}

export function RiskBadge({ level }: { level: RiskLevel | null }) {
  if (!level) {
    return (
      <span className="text-xs px-2 py-1 rounded border bg-gray-100 text-gray-600 border-gray-200">
        Not classified
      </span>
    )
  }

  return (
    <span className={`text-xs px-2 py-1 rounded border ${RISK_STYLES[level]}`}>
      {RISK_LABELS[level]}
    </span>
  )
}

const STATUS_STYLES: Record<ComplianceStatusValue, string> = {
  not_started: 'bg-gray-100 text-gray-700',
  in_progress: 'bg-blue-100 text-blue-700',
  under_review: 'bg-indigo-100 text-indigo-700',
  compliant: 'bg-green-100 text-green-700',
  non_compliant: 'bg-red-100 text-red-700',
}

export function StatusBadge({ status }: { status: ComplianceStatusValue }) {
  return (
    <span className={`text-xs px-2 py-1 rounded capitalize ${STATUS_STYLES[status]}`}>
      {status.replace(/_/g, ' ')}
    </span>
  )
}

export function ProgressBar({ value }: { value: number }) {
  const color =
    value >= 80 ? 'bg-green-500' : value >= 50 ? 'bg-yellow-500' : 'bg-red-500'

  return (
    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all ${color}`}
        style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }}
      />
    </div>
  )
}
