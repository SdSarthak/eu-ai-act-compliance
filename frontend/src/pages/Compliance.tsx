import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  CheckCircle2,
  Circle,
  ClipboardList,
  MinusCircle,
  RefreshCw,
  Timer,
} from 'lucide-react'
import { aiSystemsApi, complianceApi } from '../services/api'
import { ProgressBar, RiskBadge, StatusBadge } from '../components/RiskBadge'
import type { ComplianceItem, ItemStatus } from '../types'

const CATEGORY_LABELS: Record<string, string> = {
  risk_management: 'Risk management',
  data_governance: 'Data governance',
  documentation: 'Documentation',
  record_keeping: 'Record keeping',
  transparency: 'Transparency',
  human_oversight: 'Human oversight',
  robustness: 'Robustness and security',
  registration: 'Registration',
  governance: 'Governance',
}

const STATUS_CYCLE: ItemStatus[] = ['pending', 'in_progress', 'completed']

const STATUS_ICONS: Record<ItemStatus, typeof Circle> = {
  pending: Circle,
  in_progress: Timer,
  completed: CheckCircle2,
  not_applicable: MinusCircle,
}

const STATUS_COLORS: Record<ItemStatus, string> = {
  pending: 'text-gray-300 hover:text-gray-400',
  in_progress: 'text-yellow-500',
  completed: 'text-green-600',
  not_applicable: 'text-gray-400',
}

export default function Compliance() {
  const { systemId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [editingNotes, setEditingNotes] = useState<number | null>(null)
  const [noteDraft, setNoteDraft] = useState('')

  const { data: systems = [] } = useQuery({
    queryKey: ['ai-systems'],
    queryFn: aiSystemsApi.list,
  })

  const selectedId = systemId ? parseInt(systemId, 10) : systems[0]?.id

  useEffect(() => {
    if (!systemId && systems.length > 0) {
      navigate(`/compliance/${systems[0].id}`, { replace: true })
    }
  }, [systemId, systems, navigate])

  const { data: checklist, isLoading } = useQuery({
    queryKey: ['checklist', selectedId],
    queryFn: () => complianceApi.checklist(selectedId as number),
    enabled: Boolean(selectedId),
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['checklist', selectedId] })
    queryClient.invalidateQueries({ queryKey: ['ai-systems'] })
    queryClient.invalidateQueries({ queryKey: ['compliance-overview'] })
  }

  const updateMutation = useMutation({
    mutationFn: ({
      itemId,
      payload,
    }: {
      itemId: number
      payload: { status?: ItemStatus; evidence_notes?: string }
    }) => complianceApi.updateItem(itemId, payload),
    onSuccess: invalidate,
  })

  const syncMutation = useMutation({
    mutationFn: () => complianceApi.sync(selectedId as number),
    onSuccess: invalidate,
  })

  const advance = (item: ComplianceItem) => {
    const next =
      item.status === 'not_applicable'
        ? 'pending'
        : STATUS_CYCLE[(STATUS_CYCLE.indexOf(item.status) + 1) % STATUS_CYCLE.length]
    updateMutation.mutate({ itemId: item.id, payload: { status: next } })
  }

  const saveNotes = (item: ComplianceItem) => {
    updateMutation.mutate({
      itemId: item.id,
      payload: { evidence_notes: noteDraft },
    })
    setEditingNotes(null)
  }

  if (systems.length === 0) {
    return (
      <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
        <ClipboardList className="w-16 h-16 mx-auto mb-4 text-gray-300" />
        <h3 className="text-lg font-medium text-gray-900">Nothing to track yet</h3>
        <p className="text-gray-500 mt-1">
          Register an AI system and classify it to build its compliance checklist.
        </p>
      </div>
    )
  }

  const grouped = (checklist?.items ?? []).reduce<Record<string, ComplianceItem[]>>(
    (accumulator, item) => {
      accumulator[item.category] = [...(accumulator[item.category] ?? []), item]
      return accumulator
    },
    {}
  )

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Compliance</h1>
          <p className="text-gray-600">
            Work through the obligations that apply to each AI system
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedId ?? ''}
            onChange={(event) => navigate(`/compliance/${event.target.value}`)}
            className="px-3 py-2 border border-gray-300 rounded-lg bg-white"
          >
            {systems.map((system) => (
              <option key={system.id} value={system.id}>
                {system.name}
              </option>
            ))}
          </select>
          <button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending || !selectedId}
            className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw
              className={`w-4 h-4 ${syncMutation.isPending ? 'animate-spin' : ''}`}
            />
            Rebuild checklist
          </button>
        </div>
      </div>

      {isLoading || !checklist ? (
        <div className="text-center py-12 text-gray-500">Loading checklist...</div>
      ) : (
        <>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  {checklist.ai_system_name}
                </h2>
                <div className="flex items-center gap-2 mt-2">
                  <RiskBadge level={checklist.risk_level} />
                  <StatusBadge status={checklist.compliance_status} />
                </div>
              </div>
              <div className="text-right">
                <p className="text-3xl font-bold text-gray-900">
                  {checklist.compliance_score}%
                </p>
                <p className="text-sm text-gray-500">
                  {checklist.completed_items} of {checklist.total_items} complete
                </p>
              </div>
            </div>
            <div className="mt-4">
              <ProgressBar value={checklist.compliance_score} />
            </div>
            {Object.keys(checklist.category_scores).length > 0 && (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mt-6 pt-6 border-t border-gray-100">
                {Object.entries(checklist.category_scores).map(([category, score]) => (
                  <div key={category}>
                    <p className="text-xs text-gray-500">
                      {CATEGORY_LABELS[category] ?? category}
                    </p>
                    <p className="text-sm font-medium text-gray-900 mb-1">{score}%</p>
                    <ProgressBar value={score} />
                  </div>
                ))}
              </div>
            )}
          </div>

          {Object.entries(grouped).map(([category, items]) => (
            <div
              key={category}
              className="bg-white rounded-xl border border-gray-200 p-6"
            >
              <h3 className="font-semibold text-gray-900 mb-4">
                {CATEGORY_LABELS[category] ?? category}
              </h3>
              <div className="space-y-4">
                {items.map((item) => {
                  const Icon = STATUS_ICONS[item.status]
                  return (
                    <div
                      key={item.id}
                      className="flex items-start gap-4 p-4 rounded-lg border border-gray-100 hover:border-gray-200"
                    >
                      <button
                        onClick={() => advance(item)}
                        title="Cycle status"
                        className={`mt-0.5 ${STATUS_COLORS[item.status]}`}
                      >
                        <Icon className="w-6 h-6" />
                      </button>
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-xs font-medium bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                            {item.article}
                          </span>
                          <p
                            className={`font-medium ${
                              item.status === 'completed'
                                ? 'text-gray-400 line-through'
                                : 'text-gray-900'
                            }`}
                          >
                            {item.title}
                          </p>
                        </div>
                        {item.description && (
                          <p className="text-sm text-gray-600 mt-1">
                            {item.description}
                          </p>
                        )}

                        {editingNotes === item.id ? (
                          <div className="mt-3 space-y-2">
                            <textarea
                              value={noteDraft}
                              onChange={(event) => setNoteDraft(event.target.value)}
                              rows={2}
                              placeholder="Link to the policy, ticket or document that evidences this"
                              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                            />
                            <div className="flex gap-2">
                              <button
                                onClick={() => saveNotes(item)}
                                className="px-3 py-1 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                              >
                                Save
                              </button>
                              <button
                                onClick={() => setEditingNotes(null)}
                                className="px-3 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          <button
                            onClick={() => {
                              setEditingNotes(item.id)
                              setNoteDraft(item.evidence_notes ?? '')
                            }}
                            className="mt-2 text-sm text-primary-600 hover:text-primary-500"
                          >
                            {item.evidence_notes
                              ? `Evidence: ${item.evidence_notes}`
                              : 'Add evidence'}
                          </button>
                        )}
                      </div>
                      <button
                        onClick={() =>
                          updateMutation.mutate({
                            itemId: item.id,
                            payload: {
                              status:
                                item.status === 'not_applicable'
                                  ? 'pending'
                                  : 'not_applicable',
                            },
                          })
                        }
                        className="text-xs text-gray-400 hover:text-gray-600 whitespace-nowrap"
                      >
                        {item.status === 'not_applicable'
                          ? 'Mark applicable'
                          : 'Not applicable'}
                      </button>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  )
}
