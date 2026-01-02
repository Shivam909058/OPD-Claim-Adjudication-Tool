"use client"

import type React from "react"

import { useState, useEffect, Suspense } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Header } from "@/components/header"
import { Upload, FileText, X, Loader2, AlertCircle, ArrowLeft } from "lucide-react"
import { useRouter, useSearchParams } from "next/navigation"
import { useToast } from "@/hooks/use-toast"
import { submitAppeal, ApiError } from "@/lib/api"
import Link from "next/link"

function AppealForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [claimId, setClaimId] = useState(searchParams.get("claim_id") || "")
  const [appealReason, setAppealReason] = useState("")
  const [files, setFiles] = useState<File[]>([])

  useEffect(() => {
    const id = searchParams.get("claim_id")
    if (id) setClaimId(id)
  }, [searchParams])

  const handleFileChange = (file: File) => {
    setFiles((prev) => [...prev, file])
  }

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!claimId) {
      setSubmitError("Please enter a claim ID")
      return
    }
    
    if (!appealReason.trim()) {
      setSubmitError("Please provide a reason for your appeal")
      return
    }

    setIsSubmitting(true)
    setSubmitError(null)

    try {
      const response = await submitAppeal(claimId, {
        reason: appealReason,
        additional_documents: files.map(f => f.name),
      })

      toast({
        title: "Appeal Submitted Successfully!",
        description: response.message,
      })

      router.push("/")
    } catch (error) {
      const errorMessage = error instanceof ApiError 
        ? error.detail 
        : "Failed to submit appeal. Please try again."
      
      setSubmitError(errorMessage)
      toast({
        title: "Appeal Failed",
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

      <main className="container mx-auto px-4 py-8 max-w-3xl">
        <div className="mb-8">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-6 group"
          >
            <ArrowLeft className="h-4 w-4 group-hover:-translate-x-1 transition-transform" />
            <span className="font-semibold">Back to Dashboard</span>
          </Link>
          <h1 className="text-4xl font-bold text-balance mb-2">Submit Appeal</h1>
          <p className="text-muted-foreground text-lg">
            Provide additional information or documentation to appeal your claim decision
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Error Alert */}
          {submitError && (
            <div className="flex gap-3 p-4 bg-error/10 border-2 border-error/20 rounded-lg">
              <AlertCircle className="h-5 w-5 text-error flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-semibold text-error">Error</p>
                <p className="text-sm text-muted-foreground">{submitError}</p>
              </div>
            </div>
          )}

          {/* Info Alert */}
          <div className="flex gap-3 p-4 bg-review/10 border-2 border-review/20 rounded-lg">
            <AlertCircle className="h-5 w-5 text-review flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="font-semibold text-review">Appeal Guidelines</p>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Please provide a clear explanation for your appeal along with any supporting documents. Appeals are
                typically reviewed within 3-5 business days.
              </p>
            </div>
          </div>

          {/* Claim ID */}
          <Card className="border-2">
            <CardHeader>
              <CardTitle>Claim Information</CardTitle>
              <CardDescription>Enter the claim ID you want to appeal</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="claimId">Claim ID *</Label>
                <Input
                  id="claimId"
                  placeholder="CLM_20240115_XXXXXXXX"
                  required
                  value={claimId}
                  onChange={(e) => setClaimId(e.target.value)}
                  className="font-mono"
                />
                <p className="text-sm text-muted-foreground">
                  You can find this ID in your claim status page or email notification
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Appeal Reason */}
          <Card className="border-2">
            <CardHeader>
              <CardTitle>Appeal Reason</CardTitle>
              <CardDescription>Explain why you believe the claim decision should be reconsidered</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="appealReason">Reason for Appeal *</Label>
                <Textarea
                  id="appealReason"
                  placeholder="Please provide detailed information about why you're appealing this decision..."
                  required
                  value={appealReason}
                  onChange={(e) => setAppealReason(e.target.value)}
                  className="min-h-[200px]"
                />
                <p className="text-sm text-muted-foreground">{appealReason.length}/1000 characters</p>
              </div>
            </CardContent>
          </Card>

          {/* Additional Documents */}
          <Card className="border-2">
            <CardHeader>
              <CardTitle>Additional Documents</CardTitle>
              <CardDescription>Upload any supporting documents that strengthen your appeal</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Upload Documents (Optional)</Label>
                <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer hover:bg-muted/50 transition-colors">
                  <div className="flex flex-col items-center justify-center pt-5 pb-6">
                    <Upload className="h-8 w-8 text-muted-foreground mb-2" />
                    <p className="text-sm text-muted-foreground">Click to upload or drag and drop</p>
                    <p className="text-xs text-muted-foreground mt-1">PDF, JPG, PNG (MAX. 10MB)</p>
                  </div>
                  <input
                    type="file"
                    className="hidden"
                    accept="image/*,.pdf"
                    multiple
                    onChange={(e) => {
                      const selectedFile = e.target.files?.[0]
                      if (selectedFile) handleFileChange(selectedFile)
                    }}
                  />
                </label>
              </div>

              {files.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium">Uploaded Files ({files.length})</p>
                  <div className="space-y-2">
                    {files.map((file, index) => (
                      <div key={index} className="flex items-center justify-between p-3 border rounded-lg bg-muted/50">
                        <div className="flex items-center gap-2">
                          <FileText className="h-5 w-5 text-muted-foreground" />
                          <span className="text-sm">{file.name}</span>
                        </div>
                        <Button type="button" variant="ghost" size="sm" onClick={() => removeFile(index)}>
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="flex justify-end gap-4">
            <Button type="button" variant="outline" onClick={() => router.push("/")}>
              Cancel
            </Button>
            <Button type="submit" size="lg" disabled={isSubmitting || !claimId} className="gap-2">
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Submitting Appeal...
                </>
              ) : (
                "Submit Appeal"
              )}
            </Button>
          </div>
        </form>
      </main>
    </div>
  )
}

export default function AppealPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-background">
        <Header />
        <main className="container mx-auto px-4 py-8 max-w-3xl">
          <div className="flex flex-col items-center justify-center py-24">
            <Loader2 className="h-12 w-12 animate-spin text-primary mb-4" />
            <p className="text-lg font-medium text-muted-foreground">Loading...</p>
          </div>
        </main>
      </div>
    }>
      <AppealForm />
    </Suspense>
  )
}
