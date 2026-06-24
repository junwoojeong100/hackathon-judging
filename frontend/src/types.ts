export interface Criterion {
  id?: number
  key: string
  name: string
  description: string
  weight: number
  order: number
}

export interface CriterionScore {
  criterion_key: string
  criterion_name: string
  score: number
  weight: number
  rationale: string
}

export interface Judgment {
  id: number
  overall_score: number
  base_score: number
  azure_detected: boolean
  azure_score: number
  azure_signals: string
  ms_stack_detected: boolean
  ms_stack_score: number
  ms_stack_signals: string
  summary: string
  model: string
  created_at: string
  scores: CriterionScore[]
}

export interface Submission {
  id: number
  team_name: string
  project_name: string
  source_type: string
  source_ref: string
  deployment_url: string
  stage: string
  status: string
  error_message: string
  created_at: string
  latest_judgment: Judgment | null
}

export interface LeaderboardEntry {
  rank: number
  submission_id: number
  team_name: string
  project_name: string
  overall_score: number
  status: string
  stage: string
  attempts: number
  azure_detected: boolean
  ms_stack_detected: boolean
}
