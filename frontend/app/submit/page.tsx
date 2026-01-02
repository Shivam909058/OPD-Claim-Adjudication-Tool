"use client"

import type React from "react"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Header } from "@/components/header"
import { Upload, FileText, X, Loader2, Sparkles, AlertCircle } from "lucide-react"
import { useRouter } from "next/navigation"
import { useToast } from "@/hooks/use-toast"
import { submitClaim, transformFormDataToRequest, ApiError } from "@/lib/api"

const networkHospitals = [
  "Apollo Hospital",
  "Fortis Healthcare",
  "Max Healthcare",
  "Manipal Hospital",
  "Narayana Health",
]

const treatmentCategories = ["Consultation", "Dental", "Pharmacy", "Diagnostic", "Vision", "Alternative Medicine"]

export default function SubmitClaimPage() {
  const router = useRouter()
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    memberId: "",
    memberName: "",
    treatmentDate: "",
    hospitalName: "",
    cashlessRequest: false,
    claimAmount: "",
    treatmentCategory: "",
  })

  const [files, setFiles] = useState({
    prescription: null as File | null,
    bill: null as File | null,
    reports: [] as File[],
  })

  const [showHospitalSuggestions, setShowHospitalSuggestions] = useState(false)
  const filteredHospitals = networkHospitals.filter((hospital) =>
    hospital.toLowerCase().includes(formData.hospitalName.toLowerCase()),
  )

  const handleFileChange = (type: "prescription" | "bill" | "reports", file: File) => {
    if (type === "reports") {
      setFiles((prev) => ({ ...prev, reports: [...prev.reports, file] }))
    } else {
      setFiles((prev) => ({ ...prev, [type]: file }))
    }
  }

  const removeFile = (type: "prescription" | "bill" | "reports", index?: number) => {
    if (type === "reports" && index !== undefined) {
      setFiles((prev) => ({
        ...prev,
        reports: prev.reports.filter((_, i) => i !== index),
      }))
    } else {
      setFiles((prev) => ({ ...prev, [type]: null }))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Manual validation for file uploads
    if (!files.prescription) {
      setSubmitError("Please upload a prescription document")
      return
    }
    if (!files.bill) {
      setSubmitError("Please upload a medical bill document")
      return
    }
    
    setIsSubmitting(true)
    setSubmitError(null)

    try {
      // Transform form data to API request format
      const request = transformFormDataToRequest(formData)
      
      // Submit claim to backend
      const response = await submitClaim(request)

      // Show success toast with decision info
      const decisionMessage = response.decision === "APPROVED" 
        ? `Approved amount: ₹${response.approved_amount.toLocaleString()}`
        : response.decision === "REJECTED"
        ? `Reason: ${response.rejection_reasons[0] || "See details"}`
        : response.decision === "PARTIAL"
        ? `Partially approved: ₹${response.approved_amount.toLocaleString()}`
        : "Sent for manual review"

      toast({
        title: `Claim ${response.decision}!`,
        description: decisionMessage,
        variant: response.decision === "REJECTED" ? "destructive" : "default",
      })

      // Navigate to status page with real claim ID
      router.push(`/status/${response.claim_id}`)
    } catch (error) {
      const errorMessage = error instanceof ApiError 
        ? error.detail 
        : "Failed to submit claim. Please try again."
      
      setSubmitError(errorMessage)
      toast({
        title: "Submission Failed",
        description: errorMessage,
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="container mx-auto px-4 lg:px-8 py-12 max-w-4xl">
        <div className="mb-12">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-2 w-2 rounded-full bg-primary animate-pulse" />
            <span className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">New Submission</span>
          </div>
          <h1 className="text-5xl font-bold text-balance mb-4 leading-tight">Submit Your Claim</h1>
          <p className="text-muted-foreground text-xl leading-relaxed">
            Fill out the form below and upload your documents. Our AI will process your claim instantly.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Error Alert */}
          {submitError && (
            <div className="flex gap-3 p-4 bg-error/10 border-2 border-error/20 rounded-lg">
              <AlertCircle className="h-5 w-5 text-error flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-semibold text-error">Submission Error</p>
                <p className="text-sm text-muted-foreground">{submitError}</p>
              </div>
            </div>
          )}

          <Card className="border-2 shadow-lg overflow-hidden">
            <CardHeader className="bg-muted/30 border-b">
              <CardTitle className="text-xl font-bold">Member Details</CardTitle>
              <CardDescription className="text-base">Enter the patient information for this claim</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6 p-6 lg:p-8">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="memberId" className="text-sm font-bold">
                    Member ID *
                  </Label>
                  <Input
                    id="memberId"
                    placeholder="MEM123456"
                    required
                    value={formData.memberId}
                    onChange={(e) => setFormData({ ...formData, memberId: e.target.value })}
                    className="h-12 text-base"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="memberName" className="text-sm font-bold">
                    Member Name *
                  </Label>
                  <Input
                    id="memberName"
                    placeholder="John Doe"
                    required
                    value={formData.memberName}
                    onChange={(e) => setFormData({ ...formData, memberName: e.target.value })}
                    className="h-12 text-base"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="treatmentDate" className="text-sm font-bold">
                    Treatment Date *
                  </Label>
                  <Input
                    id="treatmentDate"
                    type="date"
                    required
                    value={formData.treatmentDate}
                    onChange={(e) => setFormData({ ...formData, treatmentDate: e.target.value })}
                    className="h-12 text-base"
                  />
                </div>
                <div className="space-y-2 relative">
                  <Label htmlFor="hospitalName" className="text-sm font-bold">
                    Hospital Name *
                  </Label>
                  <Input
                    id="hospitalName"
                    placeholder="Search network hospitals..."
                    required
                    value={formData.hospitalName}
                    onChange={(e) => setFormData({ ...formData, hospitalName: e.target.value })}
                    onFocus={() => setShowHospitalSuggestions(true)}
                    onBlur={() => setTimeout(() => setShowHospitalSuggestions(false), 200)}
                    className="h-12 text-base"
                  />
                  {showHospitalSuggestions && formData.hospitalName && filteredHospitals.length > 0 && (
                    <div className="absolute z-10 w-full mt-1 bg-popover border-2 rounded-lg shadow-xl">
                      {filteredHospitals.map((hospital) => (
                        <button
                          key={hospital}
                          type="button"
                          className="w-full text-left px-4 py-3 hover:bg-accent hover:text-accent-foreground transition-colors font-medium border-b last:border-b-0"
                          onClick={() => {
                            setFormData({ ...formData, hospitalName: hospital })
                            setShowHospitalSuggestions(false)
                          }}
                        >
                          {hospital}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center space-x-3 p-4 bg-muted/50 rounded-lg border">
                <Switch
                  id="cashless"
                  checked={formData.cashlessRequest}
                  onCheckedChange={(checked) => setFormData({ ...formData, cashlessRequest: checked })}
                />
                <div>
                  <Label htmlFor="cashless" className="cursor-pointer font-bold text-base">
                    Cashless Request
                  </Label>
                  <p className="text-sm text-muted-foreground">Request direct settlement with hospital</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-2 shadow-lg overflow-hidden">
            <CardHeader className="bg-muted/30 border-b">
              <CardTitle className="text-xl font-bold">Documents Upload</CardTitle>
              <CardDescription className="text-base">
                Upload required documents for claim processing (PDF, JPG, PNG)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6 p-6 lg:p-8">
              <div className="space-y-2">
                <Label className="text-sm font-bold">Prescription *</Label>
                <FileUploadArea
                  label="Prescription"
                  accept="image/*,.pdf"
                  file={files.prescription}
                  onChange={(file) => handleFileChange("prescription", file)}
                  onRemove={() => removeFile("prescription")}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label className="text-sm font-bold">Medical Bill *</Label>
                <FileUploadArea
                  label="Medical Bill"
                  accept="image/*,.pdf"
                  file={files.bill}
                  onChange={(file) => handleFileChange("bill", file)}
                  onRemove={() => removeFile("bill")}
                  required
                />
              </div>

              <div className="space-y-3">
                <Label className="text-sm font-bold">Diagnostic Reports (Optional)</Label>
                <FileUploadArea
                  label="Upload diagnostic reports"
                  accept="image/*,.pdf"
                  file={null}
                  onChange={(file) => handleFileChange("reports", file)}
                  onRemove={() => {}}
                  multiple
                />
                <div className="flex flex-wrap gap-3 mt-3">
                  {files.reports.map((file, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-2 bg-primary/10 border border-primary/20 px-4 py-3 rounded-lg"
                    >
                      <FileText className="h-5 w-5 text-primary" />
                      <span className="text-sm font-medium">{file.name}</span>
                      <button
                        type="button"
                        onClick={() => removeFile("reports", index)}
                        className="text-muted-foreground hover:text-foreground ml-2"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-2 shadow-lg overflow-hidden">
            <CardHeader className="bg-muted/30 border-b">
              <CardTitle className="text-xl font-bold">Claim Details</CardTitle>
              <CardDescription className="text-base">Provide claim amount and treatment category</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6 p-6 lg:p-8">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="claimAmount" className="text-sm font-bold">
                    Total Claim Amount (₹) *
                  </Label>
                  <Input
                    id="claimAmount"
                    type="number"
                    placeholder="5000"
                    required
                    value={formData.claimAmount}
                    onChange={(e) => setFormData({ ...formData, claimAmount: e.target.value })}
                    className="h-12 text-base"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="treatmentCategory" className="text-sm font-bold">
                    Treatment Category *
                  </Label>
                  <select
                    id="treatmentCategory"
                    required
                    value={formData.treatmentCategory}
                    onChange={(e) => setFormData({ ...formData, treatmentCategory: e.target.value })}
                    className="flex h-12 w-full rounded-md border-2 border-input bg-background px-4 py-2 text-base ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring font-medium"
                  >
                    <option value="">Select category</option>
                    {treatmentCategories.map((category) => (
                      <option key={category} value={category}>
                        {category}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="flex flex-col sm:flex-row justify-end gap-4 pt-4">
            <Button
              type="button"
              variant="outline"
              size="lg"
              onClick={() => router.push("/")}
              className="font-semibold"
            >
              Cancel
            </Button>
            <Button type="submit" size="lg" disabled={isSubmitting} className="gap-2 font-semibold shadow-lg px-8">
              {isSubmitting ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Submitting Claim...
                </>
              ) : (
                <>
                  <Sparkles className="h-5 w-5" />
                  Submit Claim
                </>
              )}
            </Button>
          </div>
        </form>
      </main>
    </div>
  )
}

function FileUploadArea({
  label,
  accept,
  file,
  onChange,
  onRemove,
  required = false,
  multiple = false,
}: {
  label: string
  accept: string
  file: File | null
  onChange: (file: File) => void
  onRemove: () => void
  required?: boolean
  multiple?: boolean
}) {
  return (
    <div className="space-y-3">
      {file ? (
        <div className="flex items-center justify-between p-5 border-2 border-dashed rounded-lg bg-primary/5 border-primary/30">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-primary/20 flex items-center justify-center">
              <FileText className="h-5 w-5 text-primary" />
            </div>
            <span className="text-sm font-semibold">{file.name}</span>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onRemove}
            className="hover:bg-error/10 hover:text-error"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>
      ) : (
        <label className={`flex flex-col items-center justify-center w-full h-40 border-2 border-dashed rounded-lg cursor-pointer hover:bg-muted/50 transition-all hover:border-primary/50 ${required ? 'border-primary/30' : ''}`}>
          <div className="flex flex-col items-center justify-center pt-5 pb-6">
            <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-3">
              <Upload className="h-6 w-6 text-primary" />
            </div>
            <p className="text-base font-semibold mb-1">Click to upload or drag and drop</p>
            <p className="text-sm text-muted-foreground">PDF, JPG, PNG (MAX. 10MB)</p>
          </div>
          <input
            type="file"
            className="hidden"
            accept={accept}
            multiple={multiple}
            onChange={(e) => {
              const selectedFile = e.target.files?.[0]
              if (selectedFile) onChange(selectedFile)
            }}
          />
        </label>
      )}
    </div>
  )
}
