export type LearningItemType =
  | 'paper'
  | 'concept'
  | 'method'
  | 'formula'
  | 'experiment'
  | 'limitation'

export interface LearningItem {
  item_id: string
  job_id: string
  paper_title: string
  item_type: LearningItemType
  target_concept: string
  source_excerpt: string
  evidence_refs: string[]
  due_at: string
  retrievability: number
  stability?: number | null
  difficulty?: number | null
  review_count: number
  lapse_count: number
  last_score?: number | null
  last_review_at: string
}

export interface LearningQuestion {
  session_id: string
  item_id: string
  position: number
  total: number
  question: string
  target_concept: string
  item_type: LearningItemType
  expected_answer_points: string[]
  why_it_matters: string
  answer_format: string[]
  evidence_refs: string[]
}

export interface LearningAttempt {
  attempt_id: string
  session_id: string
  item_id: string
  job_id: string
  paper_title: string
  target_concept: string
  question: string
  user_answer: string
  score: number
  rating: number
  feedback: string
  covered_points: string[]
  missing_points: string[]
  misconceptions: string[]
  improvement_steps: string[]
  reviewed_at: string
  next_due_at: string
}

export interface LearningSession {
  session_id: string
  job_id: string
  status: 'ACTIVE' | 'COMPLETED'
  total: number
  completed: number
  current?: LearningQuestion | null
  created_at: string
  updated_at: string
}

export interface LearningPaperSummary {
  job_id: string
  paper_title: string
  item_count: number
  due_count: number
  mastered_count: number
  reviewed_count: number
  last_review_at: string
}

export interface LearningOverview {
  total_items: number
  due_count: number
  mastered_count: number
  reviewed_today: number
  papers: LearningPaperSummary[]
  due_items: LearningItem[]
  recent_attempts: LearningAttempt[]
}

export interface LearningAnswerResult {
  attempt: LearningAttempt
  session: LearningSession
  warnings?: Array<{ code: string; message: string; detail?: string }>
}
