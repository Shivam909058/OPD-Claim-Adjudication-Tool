"use client"

import { useEffect, useState, use } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Header } from "@/components/header"
import { CheckCircle2, XCircle, Clock, FileText, AlertTriangle, TrendingUp, ArrowLeft, Sparkles, Loader2, RefreshCw } from "lucide-react"
import Link from "next/link"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { getClaimById, formatCurrency, formatDate, ApiError } from "@/lib/api"
import type { ClaimDetailsResponse, ClaimStatus } from "@/lib/types"

// Helper function to convert technical rejection codes to user-friendly messages
const formatRejectionReason = (reason: string): string => {
  const reasonMap: Record<string, string> = {
    // Eligibility Issues
    "POLICY_INACTIVE": "Your policy is currently inactive. Please contact support to reactivate.",
    "WAITING_PERIOD": "Your claim is within the waiting period. Coverage begins after the waiting period ends.",
    "MEMBER_NOT_COVERED": "The member is not covered under this policy.",
    
    // Documentation Issues
    "MISSING_DOCUMENTS": "Required documents are missing. Please upload all necessary documents.",
    "ILLEGIBLE_DOCUMENTS": "Some documents were not readable. Please upload clearer copies.",
    "INVALID_PRESCRIPTION": "The prescription provided is invalid or incomplete.",
    "DOCTOR_REG_INVALID": "The doctor's registration number could not be verified.",
    "DATE_MISMATCH": "The treatment date doesn't match the prescription/bill dates.",
    "PATIENT_MISMATCH": "Patient name on documents doesn't match the member name.",
    
    // Coverage Issues
    "SERVICE_NOT_COVERED": "This treatment/service is not covered under your policy.",
    "EXCLUDED_CONDITION": "This condition is excluded from coverage under your policy.",
    "PRE_AUTH_MISSING": "This treatment requires pre-authorization which was not obtained.",
    "pre_auth_required": "This treatment requires pre-authorization. Please obtain approval before proceeding.",
    
    // Limit Issues
    "ANNUAL_LIMIT_EXCEEDED": "The claim exceeds your annual coverage limit.",
    "SUB_LIMIT_EXCEEDED": "The claim exceeds the sub-limit for this category of treatment.",
    "PER_CLAIM_EXCEEDED": "The claim amount exceeds the maximum allowed per claim (₹5,000).",
    "per_claim_exceeded": "The claim amount exceeds the maximum allowed per claim (₹5,000).",
    
    // Medical Issues
    "NOT_MEDICALLY_NECESSARY": "The treatment was determined not to be medically necessary.",
    "EXPERIMENTAL_TREATMENT": "Experimental treatments are not covered under your policy.",
    "COSMETIC_PROCEDURE": "Cosmetic procedures are excluded from coverage.",
    
    // Process Issues
    "LATE_SUBMISSION": "The claim was submitted after the allowed time period.",
    "DUPLICATE_CLAIM": "A similar claim has already been processed.",
    "BELOW_MIN_AMOUNT": "The claim amount is below the minimum threshold.",
    
    // Exclusions
    "excluded_treatment": "This treatment is excluded from your policy coverage.",
    "cosmetic_excluded": "Cosmetic procedures are not covered.",
    "weight_loss_excluded": "Weight loss treatments are excluded from coverage.",
    "vitamins_excluded": "Vitamins and supplements are excluded from coverage.",
  }
  
  // Check if the reason contains any known pattern
  const lowerReason = reason.toLowerCase()
  
  // Return mapped message or clean up the original
  if (reasonMap[reason]) {
    return reasonMap[reason]
  }
  
  // Try to match partial patterns
  for (const [key, value] of Object.entries(reasonMap)) {
    if (lowerReason.includes(key.toLowerCase())) {
      return value
    }
  }
  
  // If no mapping found, make the technical code more readable
  return reason
    .replace(/_/g, " ")
    .replace(/([A-Z])/g, " $1")
    .trim()
    .split(" ")
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ")
}

// Helper function to format fraud flags into user-friendly messages
const formatFraudFlag = (flag: string): string => {
  const flagMap: Record<string, string> = {
    "invalid_doctor_registration": "The doctor's registration could not be verified",
    "suspicious_doctor_registration": "The doctor's registration needs additional verification",
    "doctor_reg_invalid": "Invalid or suspicious doctor registration",
    "multiple_claims_same_day": "Multiple claims submitted on the same day detected",
    "amount_near_limit": "Claim amount is very close to the per-claim limit",
    "high_claim_frequency": "Unusually high number of claims in a short period",
    "unusual_treatment_pattern": "Unusual combination of treatments detected",
    "duplicate_submission": "This appears to be a duplicate submission",
    "inconsistent_dates": "Inconsistent dates across documents",
  }
  
  const lowerFlag = flag.toLowerCase()
  
  if (flagMap[lowerFlag]) {
    return flagMap[lowerFlag]
  }
  
  // Try partial matching
  for (const [key, value] of Object.entries(flagMap)) {
    if (lowerFlag.includes(key) || key.includes(lowerFlag)) {
      return value
    }
  }
  
  // Clean up the flag text
  return flag
    .replace(/_/g, " ")
    .replace(/([A-Z])/g, " $1")
    .trim()
    .split(" ")
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ")
}

export default function ClaimStatusPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const [claim, setClaim] = useState<ClaimDetailsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchClaim = async () => {
    if (!id) return
    
    setLoading(true)
    setError(null)
    
    try {
      const data = await getClaimById(id)
      setClaim(data)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.status === 404 
          ? "Claim not found. It may have been deleted or the ID is incorrect."
          : err.detail
        )
      } else {
        setError("Failed to load claim details")
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchClaim()
  }, [id])

  const getStatusConfig = (status: ClaimStatus) => {
    switch (status) {
      case "APPROVED":
        return {
          color: "bg-success text-success-foreground",
          icon: <CheckCircle2 className="h-5 w-5" />,
          label: "Approved",
        }
      case "REJECTED":
        return {
          color: "bg-error text-error-foreground",
          icon: <XCircle className="h-5 w-5" />,
          label: "Rejected",
        }
      case "PENDING":
      case "PROCESSING":
        return {
          color: "bg-warning text-warning-foreground",
          icon: <Clock className="h-5 w-5" />,
          label: status === "PROCESSING" ? "Processing" : "Pending",
        }
      case "MANUAL_REVIEW":
        return {
          color: "bg-review text-review-foreground",
          icon: <AlertTriangle className="h-5 w-5" />,
          label: "Manual Review",
        }
      case "PARTIAL":
        return {
          color: "bg-primary text-primary-foreground",
          icon: <CheckCircle2 className="h-5 w-5" />,
          label: "Partially Approved",
        }
      case "UNDER_APPEAL":
        return {
          color: "bg-review text-review-foreground",
          icon: <TrendingUp className="h-5 w-5" />,
          label: "Under Appeal",
        }
      default:
        return {
          color: "bg-muted text-muted-foreground",
          icon: <FileText className="h-5 w-5" />,
          label: "Unknown",
        }
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <main className="container mx-auto px-4 lg:px-8 py-12 max-w-5xl">
          <div className="flex flex-col items-center justify-center py-24">
            <Loader2 className="h-12 w-12 animate-spin text-primary mb-4" />
            <p className="text-lg font-medium text-muted-foreground">Loading claim details...</p>
          </div>
        </main>
      </div>
    )
  }

  // Error state
  if (error || !claim) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <main className="container mx-auto px-4 lg:px-8 py-12 max-w-5xl">
          <div className="flex flex-col items-center justify-center py-24">
            <XCircle className="h-12 w-12 text-error mb-4" />
            <p className="text-lg font-medium text-error mb-2">Error Loading Claim</p>
            <p className="text-muted-foreground mb-6">{error || "Claim not found"}</p>
            <div className="flex gap-4">
              <Link href="/">
                <Button variant="outline" className="gap-2">
                  <ArrowLeft className="h-4 w-4" />
                  Back to Dashboard
                </Button>
              </Link>
              <Button onClick={fetchClaim} className="gap-2">
                <RefreshCw className="h-4 w-4" />
                Try Again
              </Button>
            </div>
          </div>
        </main>
      </div>
    )
  }

  const statusConfig = getStatusConfig(claim.decision || claim.status)
  const totalDeductions = (claim.copay_amount || 0) + (claim.excluded_amount || 0)

  // Generate timeline from claim data
  const timeline = [
    { 
      date: formatDate(claim.created_at), 
      event: "Claim Submitted", 
      status: "completed" 
    },
    { 
      date: formatDate(claim.created_at), 
      event: "Document Verification", 
      status: "completed" 
    },
    { 
      date: formatDate(claim.created_at), 
      event: "AI Processing", 
      status: "completed" 
    },
    { 
      date: formatDate(claim.updated_at), 
      event: claim.decision === "APPROVED" 
        ? "Claim Approved"
        : claim.decision === "REJECTED"
        ? "Claim Rejected"
        : claim.decision === "PARTIAL"
        ? "Partially Approved"
        : "Sent for Review",
      status: "completed" 
    },
  ]

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="container mx-auto px-4 lg:px-8 py-12 max-w-5xl">
        <div className="mb-12">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-6 group"
          >
            <ArrowLeft className="h-4 w-4 group-hover:-translate-x-1 transition-transform" />
            <span className="font-semibold">Back to Dashboard</span>
          </Link>
          <div className="flex items-start justify-between gap-4 mb-4">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="h-2 w-2 rounded-full bg-success animate-pulse" />
                <span className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
                  Claim Details
                </span>
              </div>
              <h1 className="text-5xl font-bold mb-4 leading-tight">Claim Status</h1>
            </div>
            <Badge className={`${statusConfig.color} gap-2 text-base px-4 py-2.5 font-bold shadow-lg`}>
              {statusConfig.icon}
              {statusConfig.label}
            </Badge>
          </div>
          <div className="flex flex-wrap items-center gap-4 text-muted-foreground text-lg">
            <span className="font-mono font-bold text-foreground">{claim.claim_id}</span>
            <span>•</span>
            <span>Member: {claim.member_name}</span>
            <span>•</span>
            <span>Treatment: {formatDate(claim.treatment_date)}</span>
          </div>
        </div>

        <div className="space-y-8">
          <Card className="border-2 shadow-xl overflow-hidden">
            <CardHeader className={`${claim.decision === "REJECTED" ? "bg-error/10 border-b border-error/20" : "bg-success/10 border-b border-success/20"}`}>
              <CardTitle className="text-xl font-bold flex items-center gap-2">
                <Sparkles className={`h-5 w-5 ${claim.decision === "REJECTED" ? "text-error" : "text-success"}`} />
                Decision Details
              </CardTitle>
              <CardDescription className="text-base">
                Breakdown of your claim decision and processing results
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-8 p-6 lg:p-8">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div className="space-y-2">
                  <p className="text-sm font-bold text-muted-foreground uppercase tracking-wider">Total Claimed</p>
                  <p className="text-4xl font-bold">{formatCurrency(claim.claim_amount)}</p>
                </div>
                <div className="space-y-2">
                  <p className="text-sm font-bold text-muted-foreground uppercase tracking-wider">Approved Amount</p>
                  <p className={`text-4xl font-bold ${claim.approved_amount ? "text-success" : "text-error"}`}>
                    {claim.approved_amount ? formatCurrency(claim.approved_amount) : "₹0"}
                  </p>
                </div>
                <div className="space-y-2">
                  <p className="text-sm font-bold text-muted-foreground uppercase tracking-wider">Confidence Score</p>
                  <div className="space-y-3">
                    <p className="text-4xl font-bold">{claim.confidence_score ? `${Math.round(claim.confidence_score * 100)}%` : "N/A"}</p>
                    {claim.confidence_score && (
                      <div className="h-3 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full transition-all"
                          style={{ width: `${claim.confidence_score * 100}%` }}
                        />
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Deductions */}
              {totalDeductions > 0 && (
                <div className="space-y-3">
                  <p className="text-sm font-bold uppercase tracking-wider">Deductions Applied</p>
                  <div className="space-y-3">
                    {claim.copay_amount > 0 && (
                      <div className="flex justify-between items-center p-4 bg-muted/70 rounded-lg border">
                        <span className="font-semibold">Co-pay (10%)</span>
                        <span className="font-bold text-lg">-{formatCurrency(claim.copay_amount)}</span>
                      </div>
                    )}
                    {claim.excluded_amount > 0 && (
                      <div className="flex justify-between items-center p-4 bg-muted/70 rounded-lg border">
                        <span className="font-semibold">Excluded Items</span>
                        <span className="font-bold text-lg">-{formatCurrency(claim.excluded_amount)}</span>
                      </div>
                    )}
                    {claim.network_discount > 0 && (
                      <div className="flex justify-between items-center p-4 bg-success/10 rounded-lg border border-success/20">
                        <span className="font-semibold text-success">Network Hospital Discount</span>
                        <span className="font-bold text-lg text-success">+{formatCurrency(claim.network_discount)}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Rejection Reasons */}
              {claim.rejection_reasons && claim.rejection_reasons.length > 0 && (
                <div className="space-y-3">
                  <p className="text-sm font-bold uppercase tracking-wider text-error">Rejection Reasons</p>
                  <div className="space-y-3">
                    {claim.rejection_reasons.map((reason, index) => (
                      <div key={index} className="flex items-start gap-3 p-4 bg-error/10 rounded-lg border border-error/20">
                        <XCircle className="h-5 w-5 text-error flex-shrink-0 mt-0.5" />
                        <span className="font-medium">{formatRejectionReason(reason)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Fraud Flags */}
              {claim.fraud_flags && claim.fraud_flags.length > 0 && (
                <div className="space-y-3">
                  <p className="text-sm font-bold uppercase tracking-wider text-warning">Fraud Flags</p>
                  <div className="space-y-3">
                    {claim.fraud_flags.map((flag, index) => (
                      <div key={index} className="flex items-start gap-3 p-4 bg-warning/10 rounded-lg border border-warning/20">
                        <AlertTriangle className="h-5 w-5 text-warning flex-shrink-0 mt-0.5" />
                        <span className="font-medium">{formatFraudFlag(flag)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Notes */}
              {claim.notes && (
                <div className="space-y-3">
                  <p className="text-sm font-bold uppercase tracking-wider">Processing Notes</p>
                  <div className="p-5 bg-primary/5 rounded-lg border border-primary/20">
                    <p className="leading-relaxed font-medium">{claim.notes}</p>
                  </div>
                </div>
              )}

              {/* Next Steps */}
              {claim.next_steps && (
                <div className="space-y-3">
                  <p className="text-sm font-bold uppercase tracking-wider">Next Steps</p>
                  <div className="p-5 bg-muted rounded-lg border">
                    <p className="leading-relaxed font-medium">{claim.next_steps}</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Timeline */}
          <Card className="border-2 shadow-xl overflow-hidden">
            <CardHeader className="bg-muted/30 border-b">
              <CardTitle className="text-xl font-bold">Processing Timeline</CardTitle>
              <CardDescription className="text-base">Track your claim through each processing stage</CardDescription>
            </CardHeader>
            <CardContent className="p-6 lg:p-8">
              <div className="space-y-6">
                {timeline.map((event, index) => (
                  <div key={index} className="flex gap-6">
                    <div className="flex flex-col items-center">
                      <div className={`h-12 w-12 rounded-full shadow-lg flex items-center justify-center ${
                        claim.decision === "REJECTED" && index === timeline.length - 1
                          ? "bg-error"
                          : "bg-success"
                      }`}>
                        {claim.decision === "REJECTED" && index === timeline.length - 1 
                          ? <XCircle className="h-6 w-6 text-error-foreground" />
                          : <CheckCircle2 className="h-6 w-6 text-success-foreground" />
                        }
                      </div>
                      {index < timeline.length - 1 && <div className="w-1 h-16 bg-border" />}
                    </div>
                    <div className="flex-1 pb-8">
                      <p className="font-bold text-lg mb-1">{event.event}</p>
                      <p className="text-sm text-muted-foreground font-medium">{event.date}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Claim Info */}
          <Card className="border-2 shadow-xl overflow-hidden">
            <CardHeader className="bg-muted/30 border-b">
              <CardTitle className="text-xl font-bold">Claim Information</CardTitle>
              <CardDescription className="text-base">
                Details submitted with this claim
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6 lg:p-8">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="p-4 bg-muted/50 rounded-lg">
                  <p className="text-sm font-bold text-muted-foreground mb-1 uppercase tracking-wider">Member ID</p>
                  <p className="font-bold text-lg font-mono">{claim.member_id}</p>
                </div>
                <div className="p-4 bg-muted/50 rounded-lg">
                  <p className="text-sm font-bold text-muted-foreground mb-1 uppercase tracking-wider">Member Name</p>
                  <p className="font-bold text-lg">{claim.member_name}</p>
                </div>
                {claim.hospital && (
                  <div className="p-4 bg-muted/50 rounded-lg">
                    <p className="text-sm font-bold text-muted-foreground mb-1 uppercase tracking-wider">Hospital</p>
                    <p className="font-bold text-lg">{claim.hospital}</p>
                  </div>
                )}
                <div className="p-4 bg-muted/50 rounded-lg">
                  <p className="text-sm font-bold text-muted-foreground mb-1 uppercase tracking-wider">Cashless Request</p>
                  <p className="font-bold text-lg">{claim.cashless_request ? "Yes" : "No"}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="flex flex-col sm:flex-row gap-4 pt-4">
            <Link href="/" className="flex-1">
              <Button variant="outline" size="lg" className="w-full font-semibold bg-transparent">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Dashboard
              </Button>
            </Link>
            {(claim.decision === "REJECTED" || claim.decision === "PARTIAL") && (
              <Link href={`/appeal?claim_id=${claim.claim_id}`} className="flex-1">
                <Button size="lg" className="w-full gap-2 font-semibold shadow-lg">
                  <TrendingUp className="h-4 w-4" />
                  Submit Appeal
                </Button>
              </Link>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
