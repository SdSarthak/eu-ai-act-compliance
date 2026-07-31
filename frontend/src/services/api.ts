import axios from 'axios'
import { useAuthStore } from '../stores/authStore'
import type {
  AISystem,
  AISystemDetail,
  ClassificationResult,
  ComplianceChecklist,
  ComplianceDocument,
  ComplianceItem,
  ComplianceOverview,
  DocumentTemplate,
  ItemStatus,
  Plan,
  Subscription,
  User,
} from '../types'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Requests that legitimately answer 401 to an anonymous caller. Redirecting on
// these reloads the page before the form can render the error, so a wrong
// password looked like nothing had happened at all.
const PUBLIC_ENDPOINTS = ['/auth/login', '/auth/register']

// Handle 401 errors: an expired session sends the user back to the login page,
// but a failed sign-in attempt is handed to the caller to display.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url ?? ''
    const isPublic = PUBLIC_ENDPOINTS.some((endpoint) => url.startsWith(endpoint))
    if (error.response?.status === 401 && !isPublic) {
      useAuthStore.getState().logout()
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

/** Pull a readable message out of an axios error for display in the UI. */
export function errorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string }
      if (first?.msg) return first.msg
    }
  }
  return fallback
}

// Auth API
export const authApi = {
  login: async (email: string, password: string) => {
    const formData = new URLSearchParams()
    formData.append('username', email)
    formData.append('password', password)
    const { data } = await api.post<{ access_token: string }>('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return data
  },
  register: async (userData: {
    email: string
    password: string
    full_name?: string
    company_name?: string
  }) => {
    const { data } = await api.post<User>('/auth/register', userData)
    return data
  },
  getMe: async () => {
    const { data } = await api.get<User>('/auth/me')
    return data
  },
  updateProfile: async (profile: {
    full_name?: string
    company_name?: string
  }) => {
    const { data } = await api.patch<User>('/auth/me', profile)
    return data
  },
}

// AI Systems API
export const aiSystemsApi = {
  list: async () => {
    const { data } = await api.get<AISystem[]>('/ai-systems/')
    return data
  },
  get: async (id: number) => {
    const { data } = await api.get<AISystemDetail>(`/ai-systems/${id}`)
    return data
  },
  create: async (system: {
    name: string
    description?: string
    version?: string
    use_case?: string
    sector?: string
  }) => {
    const { data } = await api.post<AISystem>('/ai-systems/', system)
    return data
  },
  update: async (id: number, system: Record<string, unknown>) => {
    const { data } = await api.put<AISystemDetail>(`/ai-systems/${id}`, system)
    return data
  },
  delete: async (id: number) => {
    await api.delete(`/ai-systems/${id}`)
  },
  recalculate: async (id: number) => {
    const { data } = await api.post<AISystemDetail>(`/ai-systems/${id}/recalculate`)
    return data
  },
}

// Classification API
export const classificationApi = {
  classify: async (answers: Record<string, unknown>) => {
    const { data } = await api.post<ClassificationResult>(
      '/classification/classify',
      answers
    )
    return data
  },
  classifyAndSave: async (systemId: number, answers: Record<string, unknown>) => {
    const { data } = await api.post<ClassificationResult>(
      `/classification/classify/${systemId}`,
      answers
    )
    return data
  },
}

// Compliance API
export const complianceApi = {
  overview: async () => {
    const { data } = await api.get<ComplianceOverview>('/compliance/overview')
    return data
  },
  checklist: async (systemId: number) => {
    const { data } = await api.get<ComplianceChecklist>(
      `/compliance/systems/${systemId}/checklist`
    )
    return data
  },
  sync: async (systemId: number) => {
    const { data } = await api.post<ComplianceChecklist>(
      `/compliance/systems/${systemId}/checklist/sync`
    )
    return data
  },
  updateItem: async (
    itemId: number,
    payload: { status?: ItemStatus; evidence_notes?: string }
  ) => {
    const { data } = await api.patch<ComplianceItem>(
      `/compliance/items/${itemId}`,
      payload
    )
    return data
  },
}

// Documents API
export const documentsApi = {
  list: async (aiSystemId?: number) => {
    const { data } = await api.get<ComplianceDocument[]>('/documents/', {
      params: aiSystemId ? { ai_system_id: aiSystemId } : undefined,
    })
    return data
  },
  get: async (id: number) => {
    const { data } = await api.get<ComplianceDocument>(`/documents/${id}`)
    return data
  },
  templates: async () => {
    const { data } = await api.get<DocumentTemplate[]>('/documents/templates')
    return data
  },
  generate: async (request: { document_type: string; ai_system_id: number }) => {
    const { data } = await api.post<ComplianceDocument>('/documents/generate', request)
    return data
  },
  generateAll: async (systemId: number) => {
    const { data } = await api.post<ComplianceDocument[]>(
      `/documents/systems/${systemId}/generate-all`
    )
    return data
  },
  update: async (
    id: number,
    payload: { title?: string; content?: string; status?: string }
  ) => {
    const { data } = await api.patch<ComplianceDocument>(`/documents/${id}`, payload)
    return data
  },
  downloadPdf: async (id: number) => {
    const { data } = await api.get<Blob>(`/documents/${id}/pdf`, {
      responseType: 'blob',
    })
    return data
  },
  delete: async (id: number) => {
    await api.delete(`/documents/${id}`)
  },
}

// Billing API
export const billingApi = {
  plans: async () => {
    const { data } = await api.get<Plan[]>('/billing/plans')
    return data
  },
  subscription: async () => {
    const { data } = await api.get<Subscription>('/billing/subscription')
    return data
  },
  checkout: async (tier: string) => {
    const { data } = await api.post<{ checkout_url: string; session_id: string }>(
      '/billing/checkout',
      { tier }
    )
    return data
  },
  portal: async () => {
    const { data } = await api.post<{ portal_url: string }>('/billing/portal')
    return data
  },
}

export default api
