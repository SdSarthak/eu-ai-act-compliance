import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { aiSystemsApi, errorMessage } from '../services/api'
import { ProgressBar, RiskBadge, StatusBadge } from '../components/RiskBadge'
import { Bot, Plus, Trash2, Edit } from 'lucide-react'
import type { AISystem } from '../types'

const SECTORS = [
  'HR Tech',
  'Finance',
  'Healthcare',
  'Education',
  'Legal',
  'Marketing',
  'Other',
]

const USE_CASES = [
  'CV Screening',
  'Candidate Ranking',
  'Performance Evaluation',
  'Credit Scoring',
  'Risk Assessment',
  'Customer Service',
  'Content Generation',
  'Other',
]

const EMPTY_FORM = {
  name: '',
  description: '',
  version: '',
  use_case: '',
  sector: '',
}

type SystemForm = typeof EMPTY_FORM

export default function AISystems() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [formData, setFormData] = useState<SystemForm>(EMPTY_FORM)
  const [error, setError] = useState('')

  const { data: systems = [], isLoading } = useQuery({
    queryKey: ['ai-systems'],
    queryFn: aiSystemsApi.list,
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['ai-systems'] })
    queryClient.invalidateQueries({ queryKey: ['compliance-overview'] })
    queryClient.invalidateQueries({ queryKey: ['subscription'] })
  }

  const closeModal = () => {
    setShowModal(false)
    setEditingId(null)
    setFormData(EMPTY_FORM)
    setError('')
  }

  const saveMutation = useMutation({
    mutationFn: (values: SystemForm) =>
      editingId === null
        ? aiSystemsApi.create(values)
        : aiSystemsApi.update(editingId, values),
    onSuccess: () => {
      invalidate()
      closeModal()
    },
    onError: (err) =>
      setError(errorMessage(err, 'Could not save the AI system. Try again.')),
  })

  const deleteMutation = useMutation({
    mutationFn: aiSystemsApi.delete,
    onSuccess: invalidate,
    onError: (err) => setError(errorMessage(err, 'Could not delete the AI system.')),
  })

  const openCreate = () => {
    setEditingId(null)
    setFormData(EMPTY_FORM)
    setError('')
    setShowModal(true)
  }

  const openEdit = (system: AISystem) => {
    setEditingId(system.id)
    setFormData({
      name: system.name,
      description: system.description ?? '',
      version: system.version ?? '',
      use_case: system.use_case ?? '',
      sector: system.sector ?? '',
    })
    setError('')
    setShowModal(true)
  }

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    saveMutation.mutate(formData)
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Systems</h1>
          <p className="text-gray-600">Manage your AI systems for compliance tracking</p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          <Plus className="w-5 h-5" />
          Add AI System
        </button>
      </div>

      {error && !showModal && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : systems.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <Bot className="w-16 h-16 mx-auto mb-4 text-gray-300" />
          <h3 className="text-lg font-medium text-gray-900">No AI systems yet</h3>
          <p className="text-gray-500 mt-1">
            Add your first AI system to start tracking compliance
          </p>
          <button
            onClick={openCreate}
            className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            Add AI System
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {systems.map((system) => (
            <div
              key={system.id}
              className="bg-white rounded-xl border border-gray-200 p-6"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-4 min-w-0">
                  <div className="p-3 bg-primary-50 rounded-lg">
                    <Bot className="w-6 h-6 text-primary-600" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-semibold text-gray-900">
                      {system.name}
                      {system.version && (
                        <span className="text-sm font-normal text-gray-500">
                          {' '}
                          v{system.version}
                        </span>
                      )}
                    </h3>
                    {system.description && (
                      <p className="text-gray-600 text-sm mt-1">{system.description}</p>
                    )}
                    <div className="flex flex-wrap items-center gap-2 mt-2">
                      {system.sector && (
                        <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                          {system.sector}
                        </span>
                      )}
                      {system.use_case && (
                        <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                          {system.use_case}
                        </span>
                      )}
                      <RiskBadge level={system.risk_level} />
                      <StatusBadge status={system.compliance_status} />
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => openEdit(system)}
                    title="Edit"
                    className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
                  >
                    <Edit className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => deleteMutation.mutate(system.id)}
                    title="Delete"
                    className="p-2 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Compliance Progress */}
              <div className="mt-4 pt-4 border-t border-gray-100">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Compliance Score</span>
                  <span className="font-medium">{system.compliance_score}%</span>
                </div>
                <div className="mt-2">
                  <ProgressBar value={system.compliance_score} />
                </div>
                <div className="flex gap-4 mt-4 text-sm">
                  <Link
                    to={`/classification/${system.id}`}
                    className="text-primary-600 hover:text-primary-500"
                  >
                    {system.risk_level ? 'Re-classify' : 'Classify risk'}
                  </Link>
                  <Link
                    to={`/compliance/${system.id}`}
                    className="text-primary-600 hover:text-primary-500"
                  >
                    Open checklist
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add / Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md max-h-full overflow-y-auto">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              {editingId === null ? 'Add AI System' : 'Edit AI System'}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg">
                  {error}
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  System Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                  placeholder="e.g., CV Screening AI"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                  rows={3}
                  placeholder="Brief description of what your AI system does"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Version
                </label>
                <input
                  type="text"
                  value={formData.version}
                  onChange={(e) => setFormData({ ...formData, version: e.target.value })}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                  placeholder="e.g., 2.1"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Sector</label>
                <select
                  value={formData.sector}
                  onChange={(e) => setFormData({ ...formData, sector: e.target.value })}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="">Select sector...</option>
                  {SECTORS.map((sector) => (
                    <option key={sector} value={sector}>
                      {sector}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Use Case
                </label>
                <select
                  value={formData.use_case}
                  onChange={(e) =>
                    setFormData({ ...formData, use_case: e.target.value })
                  }
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="">Select use case...</option>
                  {USE_CASES.map((useCase) => (
                    <option key={useCase} value={useCase}>
                      {useCase}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={closeModal}
                  className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saveMutation.isPending}
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                >
                  {saveMutation.isPending
                    ? 'Saving...'
                    : editingId === null
                    ? 'Add System'
                    : 'Save changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
