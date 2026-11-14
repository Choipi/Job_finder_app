export interface LlmConfig {
  configured: boolean
  ready: boolean
  base_url_configured: boolean
  provider: string
  mock: boolean
  scoring_model: string
  letter_model: string
}

export interface HealthFeatures {
  database: boolean
  profile: boolean
  letters: boolean
  employers: boolean
  offers: boolean
  collectors: boolean
  scoring: boolean
  scheduler: boolean
}

export interface HealthPayload {
  status: string
  service: string
  version: string
  environment: string
  time: string
  llm: LlmConfig
  features: HealthFeatures
}

export interface Profile {
  id: number
  first_name: string
  last_name: string
  email: string
  phone: string
  city: string
  headline: string
  summary: string
  cv_filename: string
  cv_text: string
  cv_uploaded_at: string | null
  has_cv_file: boolean
  letter_template: string
  created_at: string | null
  updated_at: string | null
}

export type ProfilePayload = Pick<
  Profile,
  | 'first_name'
  | 'last_name'
  | 'email'
  | 'phone'
  | 'city'
  | 'headline'
  | 'summary'
  | 'cv_text'
  | 'letter_template'
>

export type CampaignStatus = 'draft' | 'scheduled' | 'active' | 'paused' | 'finished'
export type RemotePolicy = 'any' | 'onsite' | 'hybrid' | 'remote'

export interface Campaign {
  id: number
  name: string
  keywords: string[]
  locations: string[]
  contract_types: string[]
  remote: RemotePolicy
  radius_km: number
  sources: string[]
  starts_on: string | null
  ends_on: string | null
  frequency_hours: number
  is_paused: boolean
  status: CampaignStatus
  days_remaining: number | null
  score_threshold: number
  scoring_model: string
  letter_model: string
  last_scan_at: string | null
  created_at: string | null
  updated_at: string | null
}

export type CampaignPayload = Pick<
  Campaign,
  | 'name'
  | 'keywords'
  | 'locations'
  | 'contract_types'
  | 'remote'
  | 'radius_km'
  | 'sources'
  | 'starts_on'
  | 'ends_on'
  | 'frequency_hours'
  | 'is_paused'
  | 'score_threshold'
  | 'scoring_model'
  | 'letter_model'
>

export interface SourceInfo {
  id: string
  label: string
  kind: 'api' | 'scrape'
  phase: number
  enabled_by_default: boolean
  note: string
  warning: string | null
}

export interface ModelPricing {
  input_per_million: number
  output_per_million: number
}

export interface ModelInfo {
  id: string
  label: string
  note: string
  context_window: number
  max_output: number
  pricing: ModelPricing
  supports_temperature: boolean
  free: boolean
  tags: string[]
}

export interface ModelsResponse {
  models: ModelInfo[]
  defaults: { scoring: string; letter: string }
  provider: string
  mock: boolean
}

export interface GeneratedLetterSummary {
  id: number
  job_title: string
  company: string
  subject: string
  source_url: string
  model: string
  prompt_tokens: number
  completion_tokens: number
  cost_usd: number
  duration_ms: number
  created_at: string | null
  updated_at: string | null
}

export interface GeneratedLetter extends GeneratedLetterSummary {
  body: string
  job_description: string
  instructions: string
  prompt_version: string
}

export interface LetterUsage {
  prompt_tokens: number
  completion_tokens: number
  cost_usd: number
  duration_ms: number
}

export interface LetterResponse {
  letter: GeneratedLetter
  usage: LetterUsage
  context_truncated: string[]
}

export interface LetterPayload {
  job_title: string
  company: string
  job_description: string
  source_url: string
  instructions: string
  model?: string
}

export interface LlmCall {
  id: number
  task: string
  model: string
  prompt_version: string
  status: 'ok' | 'error'
  prompt_tokens: number
  completion_tokens: number
  cost_usd: number
  duration_ms: number
  error: string
  created_at: string | null
}

export interface LlmUsage {
  totals: {
    calls: number
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
    cost_usd: number
  }
  recent: LlmCall[]
  models: number
}

export interface LlmTestResult {
  ok: boolean
  model: string
  reply: string
  duration_ms: number
  usage: {
    prompt_tokens: number
    completion_tokens: number
    cost_usd: number
  }
}

export interface EmployerSource {
  id: number
  name: string
  domain: string
  sector: string
  country: string
  city: string
  ats_type: string
  ats_slug: string
  careers_url: string
  enabled: boolean
  origin: string
  status: 'pending' | 'ready' | 'no_ats' | 'error'
  last_checked_at: string | null
  last_error: string
  offer_count: number
  created_at: string | null
  updated_at: string | null
}

export interface EmployerStats {
  total: number
  enabled: number
  ready: number
  pending: number
  no_ats: number
  errors: number
  offers: number
}

export interface EmployersResponse {
  employers: EmployerSource[]
  stats: EmployerStats
}

export interface DiscoveryResult {
  checked: number
  ready: number
  no_ats: number
  errors: number
  results: Array<{
    id: number
    name: string
    status: string
    ats_type: string
    ats_slug: string
    error: string
  }>
}

export interface CollectionOutcome {
  found: number
  new: number
  updated: number
  error: string
}

export interface CollectionResult {
  employers: number
  found: number
  new: number
  updated: number
  errors: number
  remaining: number
  results: Array<
    {
      id: number
      name: string
      ats: string
    } & CollectionOutcome
  >
}

export interface OfferSummary {
  id: number
  employer_id: number | null
  source: string
  title: string
  company: string
  location: string
  remote: string
  contract_type: string
  salary: string
  apply_url: string
  published_at: string | null
  score: number | null
  status: string
  created_at: string | null
}

export interface OfferDetail extends OfferSummary {
  description: string
  source_url: string
  external_id: string
  score_reasons: string[]
  last_seen_at: string | null
  updated_at: string | null
}

export interface CampaignFilter {
  active: boolean
  keywords: string[]
  locations: string[]
  remote: string
}
