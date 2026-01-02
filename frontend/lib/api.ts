/**
 * API Client Service for OPD Claim Adjudication Backend
 * Handles all communication with the FastAPI backend at port 7777
 */

import type {
  ClaimSubmissionRequest,
  ClaimDecisionResponse,
  ClaimDetailsResponse,
  ClaimsListResponse,
  AppealRequest,
  AppealResponse,
  PolicyTerms,
  HealthCheckResponse,
} from "./types"

// Backend API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:7777"

/**
 * Custom error class for API errors
 */
export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, message: string, detail?: string) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.detail = detail || message
  }
}

/**
 * Generic fetch wrapper with error handling
 */
async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    })

    // Parse response
    const data = await response.json()

    if (!response.ok) {
      // Handle FastAPI validation errors (returns array of error objects)
      let errorMessage = "An error occurred"
      if (data.detail) {
        if (Array.isArray(data.detail)) {
          // Pydantic validation errors
          errorMessage = data.detail.map((err: { msg?: string; loc?: string[] }) => 
            err.msg || JSON.stringify(err)
          ).join(". ")
        } else if (typeof data.detail === "string") {
          errorMessage = data.detail
        } else {
          errorMessage = JSON.stringify(data.detail)
        }
      }
      throw new ApiError(
        response.status,
        errorMessage,
        errorMessage
      )
    }

    return data as T
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    // Network error or other issues
    throw new ApiError(
      0,
      "Failed to connect to the server. Please ensure the backend is running.",
      (error as Error).message
    )
  }
}

// ==================== Health Check ====================

/**
 * Check if the backend server is healthy
 */
export async function checkHealth(): Promise<HealthCheckResponse> {
  return fetchApi<HealthCheckResponse>("/health")
}

// ==================== Claims API ====================

/**
 * Submit a new claim for adjudication
 * @param claim - Claim submission data
 * @returns Adjudication decision
 */
export async function submitClaim(
  claim: ClaimSubmissionRequest
): Promise<ClaimDecisionResponse> {
  return fetchApi<ClaimDecisionResponse>("/api/claims/submit", {
    method: "POST",
    body: JSON.stringify(claim),
  })
}

/**
 * Get details of a specific claim by ID
 * @param claimId - The claim ID to fetch
 * @returns Full claim details including decision
 */
export async function getClaimById(
  claimId: string
): Promise<ClaimDetailsResponse> {
  return fetchApi<ClaimDetailsResponse>(`/api/claims/${claimId}`)
}

/**
 * List all claims with optional filtering
 * @param memberId - Optional member ID to filter by
 * @param skip - Number of records to skip (pagination)
 * @param limit - Maximum records to return
 * @returns List of claims
 */
export async function listClaims(
  memberId?: string,
  skip = 0,
  limit = 100
): Promise<ClaimsListResponse> {
  const params = new URLSearchParams()
  if (memberId) params.append("member_id", memberId)
  params.append("skip", skip.toString())
  params.append("limit", limit.toString())

  return fetchApi<ClaimsListResponse>(`/api/claims?${params.toString()}`)
}

/**
 * Submit an appeal for a rejected claim
 * @param claimId - The claim ID to appeal
 * @param appeal - Appeal details
 * @returns Appeal response
 */
export async function submitAppeal(
  claimId: string,
  appeal: AppealRequest
): Promise<AppealResponse> {
  return fetchApi<AppealResponse>(`/api/claims/${claimId}/appeal`, {
    method: "POST",
    body: JSON.stringify({
      reason: appeal.reason,
      additional_documents: appeal.additional_documents || []
    }),
  })
}

// ==================== Policy API ====================

/**
 * Get policy terms and coverage details
 * @returns Policy configuration
 */
export async function getPolicyTerms(): Promise<PolicyTerms> {
  return fetchApi<PolicyTerms>("/api/policy/terms")
}

/**
 * Get list of excluded treatments
 * @returns Exclusions list
 */
export async function getPolicyExclusions(): Promise<{ exclusions: string[] }> {
  return fetchApi<{ exclusions: string[] }>("/api/policy/exclusions")
}

/**
 * Get list of network hospitals
 * @returns Network hospitals list
 */
export async function getNetworkHospitals(): Promise<{ network_hospitals: string[] }> {
  return fetchApi<{ network_hospitals: string[] }>("/api/policy/network-hospitals")
}

// ==================== Helper Functions ====================

/**
 * Transform form data to API request format
 */
export function transformFormDataToRequest(
  formData: {
    memberId: string
    memberName: string
    treatmentDate: string
    hospitalName: string
    cashlessRequest: boolean
    claimAmount: string
    treatmentCategory: string
  },
  extractedPrescription?: {
    doctorName?: string
    doctorReg?: string
    diagnosis?: string
    medicines?: string[]
  },
  extractedBill?: {
    consultationFee?: number
    diagnosticTests?: number
    medicines?: number
  }
): ClaimSubmissionRequest {
  // Map frontend category to backend category
  const categoryMap: Record<string, string> = {
    Consultation: "consultation",
    Dental: "dental",
    Pharmacy: "pharmacy",
    Diagnostic: "diagnostic",
    Vision: "vision",
    "Alternative Medicine": "alternative_medicine",
  }

  return {
    member_id: formData.memberId,
    member_name: formData.memberName,
    treatment_date: formData.treatmentDate,
    claim_amount: parseFloat(formData.claimAmount) || 0,
    hospital: formData.hospitalName || undefined,
    cashless_request: formData.cashlessRequest,
    category: categoryMap[formData.treatmentCategory] || undefined,
    documents: {
      prescription: extractedPrescription
        ? {
            doctor_name: extractedPrescription.doctorName,
            doctor_reg: extractedPrescription.doctorReg,
            diagnosis: extractedPrescription.diagnosis,
            medicines_prescribed: extractedPrescription.medicines || [],
          }
        : {
            doctor_name: "Dr. General Physician",
            doctor_reg: "REG/2020/12345",
            diagnosis: formData.treatmentCategory || "General Consultation",
            medicines_prescribed: [],
          },
      bill: extractedBill
        ? {
            consultation_fee: extractedBill.consultationFee || 0,
            diagnostic_tests: extractedBill.diagnosticTests || 0,
            medicines: extractedBill.medicines || 0,
            total_amount: parseFloat(formData.claimAmount) || 0,
            hospital_name: formData.hospitalName,
          }
        : {
            consultation_fee: parseFloat(formData.claimAmount) || 0,
            total_amount: parseFloat(formData.claimAmount) || 0,
            hospital_name: formData.hospitalName,
          },
    },
  }
}

/**
 * Format status for display with proper casing
 */
export function formatStatus(status: string): string {
  const statusMap: Record<string, string> = {
    PENDING: "Pending",
    PROCESSING: "Processing",
    APPROVED: "Approved",
    REJECTED: "Rejected",
    PARTIAL: "Partially Approved",
    MANUAL_REVIEW: "Manual Review",
    UNDER_APPEAL: "Under Appeal",
  }
  return statusMap[status] || status
}

/**
 * Format date for display
 */
export function formatDate(dateString: string): string {
  try {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    })
  } catch {
    return dateString
  }
}

/**
 * Format currency for display
 */
export function formatCurrency(amount: number): string {
  return `₹${amount.toLocaleString("en-IN")}`
}
