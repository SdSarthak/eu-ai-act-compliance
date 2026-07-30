export type RiskLevel = 'unacceptable' | 'high' | 'limited' | 'minimal'

export type ComplianceStatusValue =
  | 'not_started'
  | 'in_progress'
  | 'under_review'
  | 'compliant'
  | 'non_compliant'

export type ItemStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'not_applicable'

export interface User {
  id: number
  email: string
  full_name: string | null
  company_name: string | null
  subscription_tier: string
}

export interface AISystem {
  id: number
  name: string
  description: string | null
  version: string | null
  use_case: string | null
  sector: string | null
  risk_level: RiskLevel | null
  compliance_status: ComplianceStatusValue
  compliance_score: number
  created_at: string
  updated_at: string
}

export interface AISystemDetail extends AISystem {
  questionnaire_responses: Record<string, unknown> | null
  requirements_total: number
  requirements_completed: number
}

export interface ClassificationResult {
  risk_level: RiskLevel
  confidence: number
  reasons: string[]
  requirements: string[]
  next_steps: string[]
  applicable_articles: string[]
  annex_iii_areas: string[]
  prohibited: boolean
}

export interface ComplianceItem {
  id: number
  ai_system_id: number
  code: string
  article: string
  title: string
  description: string | null
  category: string
  status: ItemStatus
  evidence_notes: string | null
  completed_at: string | null
  updated_at: string
}

export interface ComplianceChecklist {
  ai_system_id: number
  ai_system_name: string
  risk_level: RiskLevel | null
  compliance_status: ComplianceStatusValue
  compliance_score: number
  total_items: number
  completed_items: number
  in_progress_items: number
  not_applicable_items: number
  category_scores: Record<string, number>
  items: ComplianceItem[]
}

export interface ComplianceOverview {
  total_systems: number
  unclassified_systems: number
  total_documents: number
  average_compliance_score: number
  systems_by_risk_level: Record<string, number>
  systems_by_status: Record<string, number>
  total_requirements: number
  open_requirements: number
  action_required: number
}

export interface ComplianceDocument {
  id: number
  title: string
  document_type: string
  status: string
  content: string | null
  file_path: string | null
  version: string
  ai_system_id: number | null
  created_at: string
  updated_at: string
}

export interface DocumentTemplate {
  document_type: string
  label: string
  available: boolean
}

export interface Plan {
  tier: string
  name: string
  price_usd_month: number
  ai_system_limit: number | null
  document_types: string[]
  features: string[]
  purchasable: boolean
}

export interface Subscription {
  tier: string
  plan_name: string
  price_usd_month: number
  ai_system_limit: number | null
  ai_systems_used: number
  ai_systems_remaining: number | null
  document_types: string[]
  stripe_customer_id: string | null
  stripe_subscription_id: string | null
  billing_enabled: boolean
}
