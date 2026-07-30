import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { aiSystemsApi, classificationApi, errorMessage } from '../services/api'
import { AlertTriangle, CheckCircle, Info, XCircle } from 'lucide-react'
import type { ClassificationResult, RiskLevel } from '../types'

const DEFAULT_ANSWERS = {
  use_case_category: 'hr_recruitment',

  // Article 5 - prohibited practices
  social_scoring: false,
  subliminal_manipulation: false,
  exploits_vulnerabilities: false,
  realtime_remote_biometric_id: false,
  predictive_policing_profiling: false,
  untargeted_facial_scraping: false,
  emotion_recognition_workplace: false,
  biometric_categorization_sensitive: false,

  // Article 6
  is_safety_component: false,
  affects_fundamental_rights: true,
  uses_biometric_data: false,
  makes_automated_decisions: true,

  // Annex III
  critical_infrastructure: false,
  education_access_or_evaluation: false,
  hr_recruitment_screening: true,
  hr_promotion_termination: false,
  essential_services_access: false,
  credit_worthiness: false,
  insurance_risk_assessment: false,
  law_enforcement: false,
  border_control: false,
  justice_system: false,
  democratic_processes: false,

  // Article 6(3) derogation
  purely_preparatory_task: false,
  human_reviews_every_decision: false,

  // Article 50
  interacts_with_humans: true,
  generates_synthetic_content: false,
  emotion_recognition: false,
  biometric_categorization: false,

  // Chapter V
  is_general_purpose_model: false,
}

type Answers = typeof DEFAULT_ANSWERS
type BooleanField = Exclude<keyof Answers, 'use_case_category'>

interface Question {
  field: BooleanField
  label: string
  help: string
}

const PROHIBITED_QUESTIONS: Question[] = [
  {
    field: 'social_scoring',
    label: 'Social scoring',
    help: 'Scores people over time from social behaviour, leading to detrimental treatment',
  },
  {
    field: 'subliminal_manipulation',
    label: 'Subliminal or manipulative techniques',
    help: 'Materially distorts behaviour in a way that causes significant harm',
  },
  {
    field: 'exploits_vulnerabilities',
    label: 'Exploits vulnerabilities',
    help: 'Targets age, disability or a specific social or economic situation',
  },
  {
    field: 'realtime_remote_biometric_id',
    label: 'Real-time remote biometric ID in public spaces',
    help: 'Live identification of people in publicly accessible spaces for law enforcement',
  },
  {
    field: 'predictive_policing_profiling',
    label: 'Predictive policing from profiling',
    help: 'Predicts criminal offences based solely on profiling or personality traits',
  },
  {
    field: 'untargeted_facial_scraping',
    label: 'Untargeted facial image scraping',
    help: 'Builds face recognition databases by scraping the internet or CCTV',
  },
  {
    field: 'emotion_recognition_workplace',
    label: 'Emotion inference at work or in education',
    help: 'Infers emotions of employees or students outside medical and safety uses',
  },
  {
    field: 'biometric_categorization_sensitive',
    label: 'Biometric categorisation of sensitive traits',
    help: 'Deduces race, political opinions, religion, sex life or sexual orientation',
  },
]

const ANNEX_III_QUESTIONS: Question[] = [
  {
    field: 'hr_recruitment_screening',
    label: 'CV screening / candidate ranking',
    help: 'Filters applications, targets job adverts or evaluates candidates',
  },
  {
    field: 'hr_promotion_termination',
    label: 'Promotion, termination or worker monitoring',
    help: 'Influences employment status, task allocation or performance monitoring',
  },
  {
    field: 'education_access_or_evaluation',
    label: 'Education access or evaluation',
    help: 'Determines admission, evaluates learning outcomes or monitors exams',
  },
  {
    field: 'credit_worthiness',
    label: 'Creditworthiness assessment',
    help: 'Evaluates creditworthiness or establishes a credit score',
  },
  {
    field: 'insurance_risk_assessment',
    label: 'Life or health insurance pricing',
    help: 'Risk assessment and pricing for life and health insurance',
  },
  {
    field: 'essential_services_access',
    label: 'Access to essential services',
    help: 'Evaluates eligibility for essential public assistance benefits',
  },
  {
    field: 'critical_infrastructure',
    label: 'Critical infrastructure safety',
    help: 'Safety component in traffic, water, gas, heating, electricity or digital infrastructure',
  },
  {
    field: 'law_enforcement',
    label: 'Law enforcement',
    help: 'Used by or on behalf of law enforcement authorities',
  },
  {
    field: 'border_control',
    label: 'Migration, asylum or border control',
    help: 'Supports migration, asylum or border control management',
  },
  {
    field: 'justice_system',
    label: 'Administration of justice',
    help: 'Assists a judicial authority with facts or the law',
  },
  {
    field: 'democratic_processes',
    label: 'Democratic processes',
    help: 'Influences elections, referendums or voting behaviour',
  },
  {
    field: 'is_safety_component',
    label: 'Safety component of a product',
    help: 'Part of a product covered by Union harmonisation legislation (Annex I)',
  },
  {
    field: 'uses_biometric_data',
    label: 'Biometric identification or categorisation',
    help: 'Remote biometric identification, categorisation or emotion recognition',
  },
  {
    field: 'affects_fundamental_rights',
    label: 'Affects fundamental rights',
    help: 'Impacts employment, education or access to essential services',
  },
  {
    field: 'makes_automated_decisions',
    label: 'Automated decision making',
    help: 'Produces decisions without meaningful human review',
  },
]

const DEROGATION_QUESTIONS: Question[] = [
  {
    field: 'purely_preparatory_task',
    label: 'Narrow procedural or preparatory task',
    help: 'Performs a narrow task that does not materially influence the outcome',
  },
  {
    field: 'human_reviews_every_decision',
    label: 'Every decision is reviewed by a human',
    help: 'A person meaningfully reviews the output before it is acted upon',
  },
]

const TRANSPARENCY_QUESTIONS: Question[] = [
  {
    field: 'interacts_with_humans',
    label: 'Direct interaction with people',
    help: 'Chatbots, assistants and any system users talk to directly',
  },
  {
    field: 'generates_synthetic_content',
    label: 'Synthetic content generation',
    help: 'Produces AI-generated audio, image, video or text',
  },
  {
    field: 'emotion_recognition',
    label: 'Emotion recognition',
    help: 'Detects or analyses emotions outside the workplace and education',
  },
  {
    field: 'biometric_categorization',
    label: 'Biometric categorisation',
    help: 'Assigns people to categories based on biometric data',
  },
  {
    field: 'is_general_purpose_model',
    label: 'General-purpose AI model',
    help: 'You are the provider of a general-purpose model, not only an application',
  },
]

const RISK_ICONS: Record<RiskLevel, JSX.Element> = {
  unacceptable: <XCircle className="w-8 h-8 text-red-600" />,
  high: <AlertTriangle className="w-8 h-8 text-orange-600" />,
  limited: <Info className="w-8 h-8 text-yellow-600" />,
  minimal: <CheckCircle className="w-8 h-8 text-green-600" />,
}

const RISK_COLORS: Record<RiskLevel, string> = {
  unacceptable: 'bg-red-50 border-red-200',
  high: 'bg-orange-50 border-orange-200',
  limited: 'bg-yellow-50 border-yellow-200',
  minimal: 'bg-green-50 border-green-200',
}

export default function Classification() {
  const { systemId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [result, setResult] = useState<ClassificationResult | null>(null)
  const [error, setError] = useState('')
  const [answers, setAnswers] = useState<Answers>(DEFAULT_ANSWERS)
  const [targetSystem, setTargetSystem] = useState<number | null>(
    systemId ? parseInt(systemId, 10) : null
  )

  const { data: systems = [] } = useQuery({
    queryKey: ['ai-systems'],
    queryFn: aiSystemsApi.list,
  })

  const classifyMutation = useMutation({
    mutationFn: () =>
      targetSystem
        ? classificationApi.classifyAndSave(targetSystem, answers)
        : classificationApi.classify(answers),
    onSuccess: (data) => {
      setResult(data)
      setError('')
      if (targetSystem) {
        queryClient.invalidateQueries({ queryKey: ['ai-systems'] })
        queryClient.invalidateQueries({ queryKey: ['checklist', targetSystem] })
        queryClient.invalidateQueries({ queryKey: ['compliance-overview'] })
      }
    },
    onError: (err) =>
      setError(errorMessage(err, 'Classification failed. Please try again.')),
  })

  const toggle = (field: BooleanField) =>
    setAnswers((current) => ({ ...current, [field]: !current[field] }))

  const renderQuestions = (questions: Question[]) => (
    <div className="space-y-3">
      {questions.map((question) => (
        <label key={question.field} className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={answers[question.field]}
            onChange={() => toggle(question.field)}
            className="mt-1"
          />
          <span className="text-sm text-gray-600">
            <strong className="text-gray-900">{question.label}</strong>
            <br />
            {question.help}
          </span>
        </label>
      ))}
    </div>
  )

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Risk Classification</h1>
        <p className="text-gray-600">
          Determine your AI system's risk level under the EU AI Act
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        {/* Questionnaire */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Classification questionnaire
          </h2>

          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Save the result to
              </label>
              <select
                value={targetSystem ?? ''}
                onChange={(event) => {
                  const value = event.target.value
                  setTargetSystem(value ? parseInt(value, 10) : null)
                  setResult(null)
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="">Preview only (do not save)</option>
                {systems.map((system) => (
                  <option key={system.id} value={system.id}>
                    {system.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Primary use case
              </label>
              <select
                value={answers.use_case_category}
                onChange={(event) =>
                  setAnswers({ ...answers, use_case_category: event.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="hr_recruitment">HR / Recruitment</option>
                <option value="credit_scoring">Credit Scoring</option>
                <option value="insurance">Insurance</option>
                <option value="healthcare">Healthcare</option>
                <option value="education">Education</option>
                <option value="law_enforcement">Law Enforcement</option>
                <option value="customer_service">Customer Service</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-1">
                Prohibited practices (Article 5)
              </h3>
              <p className="text-xs text-gray-500 mb-3">
                Any of these bans the system from the EU market.
              </p>
              {renderQuestions(PROHIBITED_QUESTIONS)}
            </div>

            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-1">
                High-risk indicators (Article 6 and Annex III)
              </h3>
              <p className="text-xs text-gray-500 mb-3">
                These trigger the full Chapter III obligations.
              </p>
              {renderQuestions(ANNEX_III_QUESTIONS)}
            </div>

            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-1">
                Derogation (Article 6(3))
              </h3>
              <p className="text-xs text-gray-500 mb-3">
                Both together can take a listed system out of the high-risk
                category. The assessment must be documented.
              </p>
              {renderQuestions(DEROGATION_QUESTIONS)}
            </div>

            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-1">
                Transparency indicators (Article 50)
              </h3>
              <p className="text-xs text-gray-500 mb-3">
                These create disclosure duties towards the people affected.
              </p>
              {renderQuestions(TRANSPARENCY_QUESTIONS)}
            </div>

            {error && (
              <div className="p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg">
                {error}
              </div>
            )}

            <button
              type="button"
              onClick={() => classifyMutation.mutate()}
              disabled={classifyMutation.isPending}
              className="w-full py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {classifyMutation.isPending
                ? 'Classifying...'
                : targetSystem
                ? 'Classify and save'
                : 'Classify risk level'}
            </button>
          </div>
        </div>

        {/* Results */}
        <div className="space-y-6">
          {result ? (
            <>
              <div className={`rounded-xl border p-6 ${RISK_COLORS[result.risk_level]}`}>
                <div className="flex items-center gap-4 mb-6">
                  {RISK_ICONS[result.risk_level]}
                  <div>
                    <h2 className="text-xl font-bold text-gray-900 capitalize">
                      {result.risk_level} risk
                    </h2>
                    <p className="text-sm text-gray-600">
                      Confidence: {Math.round(result.confidence * 100)}%
                    </p>
                  </div>
                </div>

                {result.prohibited && (
                  <div className="mb-6 p-3 bg-red-100 border border-red-200 rounded-lg text-sm text-red-800">
                    This system engages a practice prohibited by Article 5. It may
                    not be placed on the EU market in its current form.
                  </div>
                )}

                {result.applicable_articles.length > 0 && (
                  <div className="mb-6">
                    <h3 className="font-medium text-gray-900 mb-2">
                      Provisions engaged
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {result.applicable_articles.map((article) => (
                        <span
                          key={article}
                          className="text-xs bg-white/70 border border-gray-200 text-gray-700 px-2 py-1 rounded"
                        >
                          {article}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="mb-6">
                  <h3 className="font-medium text-gray-900 mb-2">
                    Classification reasons
                  </h3>
                  <ul className="space-y-2">
                    {result.reasons.map((reason) => (
                      <li
                        key={reason}
                        className="text-sm text-gray-600 flex items-start gap-2"
                      >
                        <span className="text-gray-400">-</span>
                        {reason}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="mb-6">
                  <h3 className="font-medium text-gray-900 mb-2">
                    Compliance requirements
                  </h3>
                  <ul className="space-y-2">
                    {result.requirements.map((requirement) => (
                      <li
                        key={requirement}
                        className="text-sm text-gray-600 flex items-start gap-2"
                      >
                        <CheckCircle className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                        {requirement}
                      </li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h3 className="font-medium text-gray-900 mb-2">Next steps</h3>
                  <ol className="space-y-2">
                    {result.next_steps.map((step, index) => (
                      <li
                        key={step}
                        className="text-sm text-gray-600 flex items-start gap-2"
                      >
                        <span className="w-5 h-5 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center text-xs flex-shrink-0">
                          {index + 1}
                        </span>
                        {step}
                      </li>
                    ))}
                  </ol>
                </div>
              </div>

              {targetSystem && (
                <button
                  onClick={() => navigate(`/compliance/${targetSystem}`)}
                  className="w-full py-3 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Open the compliance checklist
                </button>
              )}
            </>
          ) : (
            <div className="bg-gray-50 rounded-xl border border-gray-200 p-8 text-center">
              <AlertTriangle className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900">
                Complete the questionnaire
              </h3>
              <p className="text-gray-500 mt-2">
                Answer the questions to determine your AI system's risk
                classification under the EU AI Act. Saving the result to a system
                also builds its compliance checklist.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
