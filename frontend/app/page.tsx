"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { FileText, CheckCircle2, XCircle, Clock, TrendingUp, ArrowRight, Loader2, AlertCircle, RefreshCw } from "lucide-react"
import Link from "next/link"
import { Header } from "@/components/header"
import { listClaims, formatCurrency, checkHealth } from "@/lib/api"
import type { ClaimListItem, ClaimStatus } from "@/lib/types"

const getStatusColor = (status: ClaimStatus) => {
  switch (status) {
    case "APPROVED":
      return "bg-success text-success-foreground"
    case "REJECTED":
      return "bg-error text-error-foreground"
    case "PENDING":
    case "PROCESSING":
      return "bg-warning text-warning-foreground"
    case "MANUAL_REVIEW":
    case "UNDER_APPEAL":
      return "bg-review text-review-foreground"
    case "PARTIAL":
      return "bg-primary text-primary-foreground"
    default:
      return "bg-muted text-muted-foreground"
  }
}

const getStatusIcon = (status: ClaimStatus) => {
  switch (status) {
    case "APPROVED":
      return <CheckCircle2 className="h-4 w-4" />
    case "REJECTED":
      return <XCircle className="h-4 w-4" />
    case "PENDING":
    case "PROCESSING":
      return <Clock className="h-4 w-4" />
    case "MANUAL_REVIEW":
    case "UNDER_APPEAL":
    case "PARTIAL":
      return <FileText className="h-4 w-4" />
    default:
      return <FileText className="h-4 w-4" />
  }
}

const formatStatusLabel = (status: ClaimStatus) => {
  const labels: Record<string, string> = {
    APPROVED: "APPROVED",
    REJECTED: "REJECTED",
    PENDING: "PENDING",
    PROCESSING: "PROCESSING",
    MANUAL_REVIEW: "MANUAL REVIEW",
    UNDER_APPEAL: "UNDER APPEAL",
    PARTIAL: "PARTIAL",
  }
  return labels[status] || status
}

export default function Dashboard() {
  const [claims, setClaims] = useState<ClaimListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null)

  const fetchClaims = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // First check if backend is online
      await checkHealth()
      setBackendOnline(true)
      
      // Fetch claims
      const response = await listClaims()
      setClaims(response.claims)
    } catch (err) {
      setBackendOnline(false)
      setError(err instanceof Error ? err.message : "Failed to load claims")
      setClaims([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchClaims()
  }, [])

  // Calculate stats from real data
  const stats = {
    total: claims.length,
    approved: claims.filter((c) => c.decision === "APPROVED" || c.status === "APPROVED").length,
    rejected: claims.filter((c) => c.decision === "REJECTED" || c.status === "REJECTED").length,
    pending: claims.filter((c) => 
      c.status === "PENDING" || 
      c.status === "PROCESSING" || 
      c.status === "MANUAL_REVIEW" ||
      c.decision === "MANUAL_REVIEW"
    ).length,
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="container mx-auto px-4 lg:px-8 py-12 max-w-7xl">
        {/* Backend Status Banner */}
        {backendOnline === false && (
          <div className="mb-8 flex items-center gap-3 p-4 bg-error/10 border-2 border-error/20 rounded-lg">
            <AlertCircle className="h-5 w-5 text-error flex-shrink-0" />
            <div className="flex-1">
              <p className="font-semibold text-error">Backend Offline</p>
              <p className="text-sm text-muted-foreground">
                Cannot connect to the server. Please ensure the backend is running on port 7777.
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={fetchClaims} className="gap-2">
              <RefreshCw className="h-4 w-4" />
              Retry
            </Button>
          </div>
        )}

        {/* Hero Section */}
        <div className="mb-12">
          <div className="flex items-center gap-3 mb-4">
            <div className={`h-2 w-2 rounded-full ${backendOnline ? "bg-success" : "bg-error"} animate-pulse`} />
            <span className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              Claims Management
            </span>
          </div>
          <h1 className="text-5xl lg:text-6xl font-bold text-balance mb-4 leading-tight">
            Your Claims,
            <br />
            <span className="text-primary">Simplified</span>
          </h1>
          <p className="text-muted-foreground text-xl max-w-2xl leading-relaxed mb-6">
            Track and manage your OPD insurance claims with real-time updates and AI-powered processing.
          </p>
          <Link href="/submit">
            <Button size="lg" className="gap-2 text-base px-8 py-6 shadow-lg hover:shadow-xl transition-all">
              Submit New Claim
              <ArrowRight className="h-5 w-5" />
            </Button>
          </Link>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          <Card className="border-2 hover:shadow-lg transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <CardTitle className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Total Claims
              </CardTitle>
              <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <FileText className="h-5 w-5 text-primary" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold mb-1">{stats.total}</div>
              <p className="text-sm text-muted-foreground">All time submissions</p>
            </CardContent>
          </Card>

          <Card className="border-2 border-success/30 bg-success/5 hover:shadow-lg transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <CardTitle className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Approved
              </CardTitle>
              <div className="h-10 w-10 rounded-lg bg-success/20 flex items-center justify-center">
                <CheckCircle2 className="h-5 w-5 text-success" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold text-success mb-1">{stats.approved}</div>
              <p className="text-sm text-muted-foreground">Successfully processed</p>
            </CardContent>
          </Card>

          <Card className="border-2 border-error/30 bg-error/5 hover:shadow-lg transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <CardTitle className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Rejected
              </CardTitle>
              <div className="h-10 w-10 rounded-lg bg-error/20 flex items-center justify-center">
                <XCircle className="h-5 w-5 text-error" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold text-error mb-1">{stats.rejected}</div>
              <p className="text-sm text-muted-foreground">Declined claims</p>
            </CardContent>
          </Card>

          <Card className="border-2 border-warning/30 bg-warning/5 hover:shadow-lg transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <CardTitle className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Pending
              </CardTitle>
              <div className="h-10 w-10 rounded-lg bg-warning/20 flex items-center justify-center">
                <Clock className="h-5 w-5 text-warning" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold text-warning mb-1">{stats.pending}</div>
              <p className="text-sm text-muted-foreground">Under review</p>
            </CardContent>
          </Card>
        </div>

        {/* Recent Claims Section */}
        <Card className="border-2 shadow-lg">
          <CardHeader className="border-b bg-muted/30">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <CardTitle className="text-2xl font-bold mb-2">Recent Claims</CardTitle>
                <p className="text-sm text-muted-foreground">Your latest claim submissions and their status</p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="lg" onClick={fetchClaims} className="gap-2" disabled={loading}>
                  <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                  Refresh
                </Button>
                <Link href="/submit">
                  <Button size="lg" className="gap-2">
                    <TrendingUp className="h-4 w-4" />
                    New Claim
                  </Button>
                </Link>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="flex flex-col items-center justify-center py-16">
                <Loader2 className="h-10 w-10 animate-spin text-primary mb-4" />
                <p className="text-muted-foreground font-medium">Loading claims...</p>
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center py-16">
                <AlertCircle className="h-10 w-10 text-error mb-4" />
                <p className="text-error font-medium mb-2">Failed to load claims</p>
                <p className="text-sm text-muted-foreground mb-4">{error}</p>
                <Button variant="outline" onClick={fetchClaims} className="gap-2">
                  <RefreshCw className="h-4 w-4" />
                  Try Again
                </Button>
              </div>
            ) : claims.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16">
                <FileText className="h-10 w-10 text-muted-foreground mb-4" />
                <p className="text-lg font-medium mb-2">No claims yet</p>
                <p className="text-sm text-muted-foreground mb-4">Submit your first claim to get started</p>
                <Link href="/submit">
                  <Button className="gap-2">
                    <TrendingUp className="h-4 w-4" />
                    Submit Claim
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-muted/50">
                    <tr className="border-b">
                      <th className="text-left py-4 px-6 font-bold text-sm uppercase tracking-wider">Claim ID</th>
                      <th className="text-left py-4 px-6 font-bold text-sm uppercase tracking-wider">Member</th>
                      <th className="text-left py-4 px-6 font-bold text-sm uppercase tracking-wider">Date</th>
                      <th className="text-left py-4 px-6 font-bold text-sm uppercase tracking-wider">Amount</th>
                      <th className="text-left py-4 px-6 font-bold text-sm uppercase tracking-wider">Approved</th>
                      <th className="text-left py-4 px-6 font-bold text-sm uppercase tracking-wider">Status</th>
                      <th className="text-left py-4 px-6 font-bold text-sm uppercase tracking-wider">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {claims.map((claim, index) => (
                      <tr
                        key={claim.claim_id}
                        className={`border-b hover:bg-muted/50 transition-colors ${index % 2 === 0 ? "bg-card" : "bg-muted/20"}`}
                      >
                        <td className="py-5 px-6 font-mono text-sm font-bold">{claim.claim_id}</td>
                        <td className="py-5 px-6 text-sm font-medium">{claim.member_name}</td>
                        <td className="py-5 px-6 text-sm font-medium">
                          {new Date(claim.treatment_date).toLocaleDateString("en-US", {
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                          })}
                        </td>
                        <td className="py-5 px-6 text-base font-bold">{formatCurrency(claim.claim_amount)}</td>
                        <td className="py-5 px-6 text-base font-bold text-success">
                          {claim.approved_amount ? formatCurrency(claim.approved_amount) : "-"}
                        </td>
                        <td className="py-5 px-6">
                          <Badge className={`${getStatusColor(claim.decision || claim.status)} gap-1.5 px-3 py-1.5 font-semibold`}>
                            {getStatusIcon(claim.decision || claim.status)}
                            {formatStatusLabel(claim.decision || claim.status)}
                          </Badge>
                        </td>
                        <td className="py-5 px-6">
                          <Link href={`/status/${claim.claim_id}`}>
                            <Button variant="outline" size="sm" className="gap-2 font-semibold bg-transparent">
                              View Details
                              <ArrowRight className="h-3 w-3" />
                            </Button>
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
