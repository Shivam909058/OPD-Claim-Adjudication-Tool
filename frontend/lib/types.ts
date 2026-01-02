/**
 * TypeScript types for OPD Claim Adjudication API
 * These types match the backend Pydantic models
 */

// Enum types
export type ClaimStatus = "PENDING" | "PROCESSING" | "APPROVED" | "REJECTED" | "PARTIAL" | "MANUAL_REVIEW" | "UNDER_APPEAL"

export type ClaimCategory = "consultation" | "diagnostic" | "pharmacy" | "dental" | "vision" | "alternative_medicine"

// Request types
export interface ClaimSubmissionRequest {
  member_id: string
  member_name: string
  treatment_date: string
  claim_amount: number
  hospital?: string
  cashless_request: boolean
  category?: string
  member_join_date?: string
  documents: {
    prescription?: {
      doctor_name?: string
      doctor_reg?: string
      diagnosis?: string
      medicines_prescribed?: string[]
      tests_prescribed?: string[]
      procedures?: string[]
    }
    bill?: {
      consultation_fee?: number
      diagnostic_tests?: number
      medicines?: number
      procedures?: number
      test_names?: string[]
      total_amount?: number
      hospital_name?: string
    }
  }
}

export interface AppealRequest {
  reason: string
  additional_documents?: string[]
}

// Response types
export interface ClaimDecisionResponse {
  claim_id: string
  decision: ClaimStatus
  approved_amount: number
  deductions: {
    copay?: number
    excluded_items?: number
    over_limit?: number
  }
  rejected_items: string[]
  rejection_reasons: string[]
  confidence_score: number
  fraud_flags: string[]
  cashless_approved: boolean
  network_discount: number
  notes: string
  next_steps: string
  created_at: string
}

export interface ClaimDetailsResponse {
  claim_id: string
  member_id: string
  member_name: string
  treatment_date: string
  claim_amount: number
  hospital: string | null
  cashless_request: boolean
  status: ClaimStatus
  decision: ClaimStatus | null
  approved_amount: number | null
  rejection_reasons: string[]
  rejected_items: string[]
  confidence_score: number | null
  notes: string | null
  next_steps: string | null
  fraud_flags: string[]
  copay_amount: number
  network_discount: number
  excluded_amount: number
  created_at: string
  updated_at: string
}

export interface ClaimListItem {
  claim_id: string
  member_id: string
  member_name: string
  treatment_date: string
  claim_amount: number
  status: ClaimStatus
  decision: ClaimStatus | null
  approved_amount: number | null
  created_at: string
  updated_at: string
}

export interface ClaimsListResponse {
  total_claims: number
  claims: ClaimListItem[]
}

export interface AppealResponse {
  claim_id: string
  appeal_id: string
  status: string
  message: string
}

export interface PolicyTerms {
  policy_id: string
  policy_name: string
  annual_limit: number
  per_claim_limit: number
  sub_limits: {
    consultation: number
    diagnostic: number
    pharmacy: number
    dental: number
    vision: number
    alternative_medicine: number
  }
  co_pay_percentage: number
  deductible: number
  waiting_period_days: number
  network_hospital_discount: number
  exclusions: string[]
}

export interface HealthCheckResponse {
  status: string
  version: string
  timestamp: string
}

// Frontend-specific types for UI state
export interface ClaimFormData {
  memberId: string
  memberName: string
  treatmentDate: string
  hospitalName: string
  cashlessRequest: boolean
  claimAmount: string
  treatmentCategory: string
}

export interface ClaimFiles {
  prescription: File | null
  bill: File | null
  reports: File[]
}

// Dashboard stats
export interface DashboardStats {
  totalClaims: number
  approved: number
  pending: number
  rejected: number
  totalApproved: number
}

// Mapped claim for UI display
export interface DisplayClaim {
  id: string
  date: string
  amount: number
  status: ClaimStatus
  approvedAmount?: number
  memberName: string
}
