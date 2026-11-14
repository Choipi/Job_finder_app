export interface LlmConfig {
  configured: boolean
  base_url_configured: boolean
  scoring_model: string
  letter_model: string
}

export interface HealthFeatures {
  database: boolean
  profile: boolean
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
