export type UnderstandingStatusCode =
  | 'SUCCESS'
  | 'DEGRADED_STRUCTURAL'
  | 'BASELINE_ONLY'
  | 'BLOCKED_UNDERSTANDING'
  | 'FAILED'
  | (string & {})

export interface WorkspaceWarning {
  code: string
  message: string
}

export interface UnderstandingStatus {
  status: UnderstandingStatusCode
  blocking_reason?: string
  warnings?: WorkspaceWarning[]
  component_status?: Record<string, string>
  allowed_downstream?: Record<string, boolean>
}

export interface PaperWorkspaceStatus {
  blocking_reason?: string
  source_type?: string
  verification_status?: string
  pdf_metadata_check?: string
  pdf_title_match?: string
  can_enter_m2?: boolean
  source_confidence?: string | number
  canonicalization_status?: string
  m2_ready?: boolean
  degradation_reason?: string
  formula_origin?: string
  formula_ocr_status?: string
  evidence_status?: string
  quality_status?: string
  [key: string]: unknown
}

export interface EvidenceText {
  text?: string
  evidence_ref?: string
  [key: string]: unknown
}

export interface PaperCard {
  title?: string
  paper_title?: string
  one_sentence_summary?: string
  thirty_second?: string
  five_minute?: string
  deep_dive?: string
  evidence_status?: string
  problem?: EvidenceText
  core_idea?: EvidenceText
  method_overview?: EvidenceText
  experiment_summary?: EvidenceText
  [key: string]: unknown
}

export interface FormulaSymbol {
  symbol: string
  meaning?: string
}

export interface FormulaTerm {
  term: string
  meaning?: string
  encourages?: string
  penalizes?: string
  if_removed?: string
}

export interface FormulaCard {
  formula_id?: string
  formula_ref?: string
  evidence_ref?: string
  formula_latex?: string
  formula_raw?: string
  display_title?: string
  purpose?: string
  problem?: string
  plain_summary?: string
  intuition?: string
  numeric_example?: string
  remove_effect?: string
  what_if_removed?: string
  weight_change_effect?: string
  weight_sensitivity?: string
  formula_origin?: string
  formula_ocr_status?: string
  evidence_status?: string
  derivation_status?: string
  coverage_status?: string
  location?: string
  symbols?: FormulaSymbol[]
  terms?: FormulaTerm[]
  [key: string]: unknown
}

export interface TeachingCard {
  card_id?: string
  title?: string
  target_type?: string
  card_type?: string
  human_explanation?: string
  evidence_ref?: string
  evidence_refs?: string[]
  [key: string]: unknown
}

export interface WorkspaceCards {
  paper_card?: PaperCard
  formula_cards?: FormulaCard[] | { formula_cards?: FormulaCard[] }
  teaching_cards?: { teaching_cards?: TeachingCard[] }
}

export interface UnderstandingStatusResponse {
  understanding_status: UnderstandingStatus
  paper_workspace_status?: PaperWorkspaceStatus
}

export interface CardsResponse {
  status: UnderstandingStatusCode
  cards: WorkspaceCards
  degraded?: boolean
  missing_components?: string[]
  paper_workspace_status?: PaperWorkspaceStatus
}

export interface ReparseResponse {
  job_id: string
}

export interface FormulaEntry {
  id: string
  index: number
  card: FormulaCard
  title: string
}

export type WorkspaceTab = 'paper' | 'formulas' | 'teaching'

export interface WorkspaceTabItem {
  key: WorkspaceTab
  label: string
  count: number
  disabled: boolean
}
