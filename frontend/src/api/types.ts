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
