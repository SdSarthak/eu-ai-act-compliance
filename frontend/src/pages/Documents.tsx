import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { aiSystemsApi, documentsApi, errorMessage } from '../services/api'
import { FileDown, FileText, Layers, Trash2, Plus, Lock } from 'lucide-react'
import type { ComplianceDocument } from '../types'

const STATUS_STYLES: Record<string, string> = {
  approved: 'bg-green-100 text-green-700',
  reviewed: 'bg-blue-100 text-blue-700',
  generated: 'bg-yellow-100 text-yellow-700',
  draft: 'bg-gray-100 text-gray-700',
  archived: 'bg-gray-100 text-gray-500',
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

export default function Documents() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [selectedSystem, setSelectedSystem] = useState<number | null>(null)
  const [selectedType, setSelectedType] = useState('risk_assessment')
  const [error, setError] = useState('')

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: () => documentsApi.list(),
  })

  const { data: systems = [] } = useQuery({
    queryKey: ['ai-systems'],
    queryFn: aiSystemsApi.list,
  })

  const { data: templates = [] } = useQuery({
    queryKey: ['document-templates'],
    queryFn: documentsApi.templates,
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['documents'] })
    queryClient.invalidateQueries({ queryKey: ['compliance-overview'] })
  }

  const generateMutation = useMutation({
    mutationFn: documentsApi.generate,
    onSuccess: () => {
      invalidate()
      setShowModal(false)
      setError('')
    },
    onError: (err) =>
      setError(errorMessage(err, 'Could not generate the document.')),
  })

  const generateAllMutation = useMutation({
    mutationFn: documentsApi.generateAll,
    onSuccess: () => {
      invalidate()
      setShowModal(false)
      setError('')
    },
    onError: (err) =>
      setError(errorMessage(err, 'Could not generate the document pack.')),
  })

  const deleteMutation = useMutation({
    mutationFn: documentsApi.delete,
    onSuccess: invalidate,
  })

  const pdfMutation = useMutation({
    mutationFn: async (doc: ComplianceDocument) => {
      const blob = await documentsApi.downloadPdf(doc.id)
      downloadBlob(blob, `${doc.title}.pdf`)
    },
    onError: (err) => setError(errorMessage(err, 'Could not export the PDF.')),
  })

  const handleGenerate = () => {
    if (!selectedSystem) return
    setError('')
    generateMutation.mutate({
      document_type: selectedType,
      ai_system_id: selectedSystem,
    })
  }

  const availableTemplates = templates.filter((template) => template.available)
  const lockedTemplates = templates.filter((template) => !template.available)

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
          <p className="text-gray-600">
            Generate and manage compliance documentation
          </p>
        </div>
        <button
          onClick={() => {
            setError('')
            setSelectedSystem(systems[0]?.id ?? null)
            setSelectedType(availableTemplates[0]?.document_type ?? 'risk_assessment')
            setShowModal(true)
          }}
          disabled={systems.length === 0}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
        >
          <Plus className="w-5 h-5" />
          Generate Document
        </button>
      </div>

      {systems.length === 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-yellow-800 text-sm">
          You need to add an AI system first before generating documents.
        </div>
      )}

      {error && !showModal && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {lockedTemplates.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 text-sm text-gray-600 flex items-start gap-3">
          <Lock className="w-4 h-4 mt-0.5 text-gray-400 flex-shrink-0" />
          <span>
            {lockedTemplates.map((template) => template.label).join(', ')}{' '}
            {lockedTemplates.length === 1 ? 'is' : 'are'} not included in your
            current plan.
          </span>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : documents.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <FileText className="w-16 h-16 mx-auto mb-4 text-gray-300" />
          <h3 className="text-lg font-medium text-gray-900">No documents yet</h3>
          <p className="text-gray-500 mt-1">
            Generate your first compliance document
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {documents.map((doc) => (
            <div key={doc.id} className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-4 min-w-0">
                  <div className="p-3 bg-primary-50 rounded-lg">
                    <FileText className="w-6 h-6 text-primary-600" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-semibold text-gray-900">{doc.title}</h3>
                    <div className="flex flex-wrap items-center gap-3 mt-2">
                      <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                        {doc.document_type.replace(/_/g, ' ')}
                      </span>
                      <span
                        className={`text-xs px-2 py-1 rounded ${
                          STATUS_STYLES[doc.status] ?? STATUS_STYLES.draft
                        }`}
                      >
                        {doc.status}
                      </span>
                      <span className="text-xs text-gray-500">v{doc.version}</span>
                      <span className="text-xs text-gray-500">
                        {new Date(doc.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() =>
                      downloadBlob(
                        new Blob([doc.content ?? ''], { type: 'text/markdown' }),
                        `${doc.title}.md`
                      )
                    }
                    title="Download Markdown"
                    className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
                  >
                    <FileText className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => pdfMutation.mutate(doc)}
                    disabled={pdfMutation.isPending}
                    title="Download PDF"
                    className="p-2 text-gray-400 hover:text-primary-600 rounded-lg hover:bg-primary-50 disabled:opacity-50"
                  >
                    <FileDown className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => deleteMutation.mutate(doc.id)}
                    title="Delete"
                    className="p-2 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Preview */}
              {doc.content && (
                <div className="mt-4 pt-4 border-t border-gray-100">
                  <pre className="text-xs text-gray-600 bg-gray-50 p-3 rounded-lg overflow-auto max-h-32 whitespace-pre-wrap">
                    {doc.content.slice(0, 500)}
                    {doc.content.length > 500 ? '...' : ''}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Generate Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Generate Document
            </h2>
            <div className="space-y-4">
              {error && (
                <div className="p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg">
                  {error}
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  AI System
                </label>
                <select
                  value={selectedSystem ?? ''}
                  onChange={(e) => setSelectedSystem(parseInt(e.target.value, 10))}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="">Select AI system...</option>
                  {systems.map((system) => (
                    <option key={system.id} value={system.id}>
                      {system.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Document Type
                </label>
                <select
                  value={selectedType}
                  onChange={(e) => setSelectedType(e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  {availableTemplates.map((template) => (
                    <option key={template.document_type} value={template.document_type}>
                      {template.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-wrap justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false)
                    setError('')
                  }}
                  className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    if (!selectedSystem) return
                    setError('')
                    generateAllMutation.mutate(selectedSystem)
                  }}
                  disabled={!selectedSystem || generateAllMutation.isPending}
                  className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                >
                  <Layers className="w-4 h-4" />
                  {generateAllMutation.isPending ? 'Generating...' : 'Generate all'}
                </button>
                <button
                  onClick={handleGenerate}
                  disabled={!selectedSystem || generateMutation.isPending}
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                >
                  {generateMutation.isPending ? 'Generating...' : 'Generate'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
