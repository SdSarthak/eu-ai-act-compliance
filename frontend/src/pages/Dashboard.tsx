import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { aiSystemsApi, complianceApi } from '../services/api'
import { ProgressBar, RiskBadge, StatusBadge } from '../components/RiskBadge'
import {
  AlertTriangle,
  Bot,
  ClipboardList,
  FileText,
  Gauge,
} from 'lucide-react'

export default function Dashboard() {
  const { data: systems = [] } = useQuery({
    queryKey: ['ai-systems'],
    queryFn: aiSystemsApi.list,
  })

  const { data: overview } = useQuery({
    queryKey: ['compliance-overview'],
    queryFn: complianceApi.overview,
  })

  const stats = [
    {
      name: 'AI Systems',
      value: overview?.total_systems ?? 0,
      icon: Bot,
      color: 'bg-blue-500',
      hint: `${overview?.unclassified_systems ?? 0} not yet classified`,
    },
    {
      name: 'Average compliance',
      value: `${overview?.average_compliance_score ?? 0}%`,
      icon: Gauge,
      color: 'bg-emerald-500',
      hint: `${overview?.open_requirements ?? 0} obligations open`,
    },
    {
      name: 'Needs attention',
      value: overview?.action_required ?? 0,
      icon: AlertTriangle,
      color: 'bg-red-500',
      hint: `${overview?.systems_by_risk_level?.high ?? 0} high risk`,
    },
    {
      name: 'Documents',
      value: overview?.total_documents ?? 0,
      icon: FileText,
      color: 'bg-indigo-500',
      hint: 'Generated compliance artefacts',
    },
  ]

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600">Overview of your EU AI Act compliance status</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <div
            key={stat.name}
            className="bg-white rounded-xl shadow-sm border border-gray-200 p-6"
          >
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-lg ${stat.color}`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
              <div className="min-w-0">
                <p className="text-sm text-gray-600">{stat.name}</p>
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-3 truncate">{stat.hint}</p>
          </div>
        ))}
      </div>

      {/* Risk distribution */}
      {overview && overview.total_systems > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Portfolio by risk level
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {(['unacceptable', 'high', 'limited', 'minimal'] as const).map((level) => (
              <div key={level} className="p-4 rounded-lg border border-gray-200">
                <RiskBadge level={level} />
                <p className="text-2xl font-bold text-gray-900 mt-2">
                  {overview.systems_by_risk_level[level] ?? 0}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Link
            to="/ai-systems"
            className="flex items-center gap-3 p-4 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors"
          >
            <Bot className="w-5 h-5 text-primary-600" />
            <span className="font-medium">Add AI System</span>
          </Link>
          <Link
            to="/classification"
            className="flex items-center gap-3 p-4 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors"
          >
            <AlertTriangle className="w-5 h-5 text-primary-600" />
            <span className="font-medium">Classify Risk</span>
          </Link>
          <Link
            to="/compliance"
            className="flex items-center gap-3 p-4 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors"
          >
            <ClipboardList className="w-5 h-5 text-primary-600" />
            <span className="font-medium">Work the Checklist</span>
          </Link>
          <Link
            to="/documents"
            className="flex items-center gap-3 p-4 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors"
          >
            <FileText className="w-5 h-5 text-primary-600" />
            <span className="font-medium">Generate Documents</span>
          </Link>
        </div>
      </div>

      {/* Recent AI Systems */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Your AI Systems</h2>
        {systems.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Bot className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p>No AI systems registered yet</p>
            <Link
              to="/ai-systems"
              className="text-primary-600 hover:text-primary-500 mt-2 inline-block"
            >
              Add your first AI system
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {systems.slice(0, 5).map((system) => (
              <div
                key={system.id}
                className="flex items-center justify-between gap-4 p-4 rounded-lg border border-gray-200"
              >
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-gray-900 truncate">{system.name}</p>
                  <div className="flex flex-wrap items-center gap-2 mt-1">
                    <RiskBadge level={system.risk_level} />
                    <StatusBadge status={system.compliance_status} />
                  </div>
                  <div className="mt-3 max-w-xs">
                    <ProgressBar value={system.compliance_score} />
                  </div>
                </div>
                <Link
                  to={
                    system.risk_level
                      ? `/compliance/${system.id}`
                      : `/classification/${system.id}`
                  }
                  className="text-sm text-primary-600 hover:text-primary-500 whitespace-nowrap"
                >
                  {system.risk_level ? 'Open checklist' : 'Classify now'}
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
