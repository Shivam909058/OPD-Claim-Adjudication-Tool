# Frontend-Backend Integration Guide

This document explains how to run and test the OPD Claim Adjudication Tool with the integrated frontend and backend.

## Prerequisites

1. **Python 3.9+** with virtual environment
2. **Node.js 18+** with npm/pnpm
3. **OpenAI API Key** for AI processing

## Quick Start

### Step 1: Start the Backend

```bash
# Navigate to project root
cd opd_verify_tool

# Activate Python virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies (if not done)
pip install -r requirements.txt

# Set OpenAI API Key (if not in .env)
# Windows:
set OPENAI_API_KEY=your_key_here
# Linux/Mac:
export OPENAI_API_KEY=your_key_here

# Start the backend server
python -m app.main
```

The backend will start at **http://localhost:7777**

### Step 2: Start the Frontend

```bash
# In a new terminal, navigate to frontend
cd opd_verify_tool/frontend

# Install dependencies (if not done)
npm install
# or
pnpm install

# Start the development server
npm run dev
# or
pnpm dev
```

The frontend will start at **http://localhost:3000**

## API Integration Summary

### Endpoints Used

| Frontend Page | API Endpoint | Method | Description |
|---------------|--------------|--------|-------------|
| Dashboard | `/api/claims` | GET | List all claims |
| Submit Claim | `/api/claims/submit` | POST | Submit new claim |
| Claim Status | `/api/claims/{id}` | GET | Get claim details |
| Appeal | `/api/claims/{id}/appeal` | POST | Submit appeal |
| Health Check | `/health` | GET | Backend status |

### Request/Response Flow

1. **Submit Claim**:
   - User fills form → Frontend transforms data → POST to backend
   - Backend processes with AI agents → Returns decision
   - Frontend redirects to status page with claim ID

2. **View Claims**:
   - Frontend fetches `/api/claims` on load
   - Displays claims in table with status badges
   - Clicking "View Details" navigates to status page

3. **Claim Status**:
   - Frontend fetches `/api/claims/{id}` with claim ID from URL
   - Displays full decision details, deductions, flags
   - Shows appeal button if rejected/partial

4. **Submit Appeal**:
   - Frontend sends appeal reason to `/api/claims/{id}/appeal`
   - Backend updates claim status to "UNDER_APPEAL"
   - Frontend redirects to dashboard

## Environment Variables

### Backend (.env)
```env
OPENAI_API_KEY=your_openai_key
DEBUG=true
HOST=0.0.0.0
PORT=7777
DATABASE_URL=sqlite:///./claims.db
```

### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:7777
```

## Testing the Integration

### 1. Test Claim Submission

Submit a claim with these test values:
- Member ID: `EMP001`
- Member Name: `Test User`
- Treatment Date: Today's date
- Hospital: `Apollo Hospital` (network hospital for discount)
- Cashless Request: No
- Claim Amount: `2000`
- Category: `Consultation`

Expected: Claim should be processed and show APPROVED with co-pay deduction.

### 2. Test Rejection Scenario

Submit with:
- Member ID: `NEW001`
- Member Join Date: Today (within 30-day waiting period)
- Claim Amount: `1000`

Expected: Should be REJECTED due to waiting period.

### 3. Test Appeal Flow

1. Find a rejected claim on dashboard
2. Click "View Details"
3. Click "Submit Appeal"
4. Enter appeal reason
5. Submit

Expected: Appeal submitted, claim status changes to UNDER_APPEAL.

## Troubleshooting

### Backend Not Connecting

- Check if backend is running on port 7777
- Verify CORS is enabled (it is by default)
- Check browser console for network errors

### AI Processing Errors

- Verify OPENAI_API_KEY is set correctly
- Check backend logs for API errors
- Try with smaller claim amounts first

### Frontend Build Errors

- Run `npm install` to ensure all dependencies
- Check TypeScript errors with `npm run type-check`
- Clear `.next` folder and rebuild

## Architecture Overview

```
Frontend (Next.js :3000)
    │
    ├── lib/api.ts        → API client functions
    ├── lib/types.ts      → TypeScript types
    │
    └── Pages
        ├── / (Dashboard)       → listClaims()
        ├── /submit             → submitClaim()
        ├── /status/[id]        → getClaimById()
        └── /appeal             → submitAppeal()

Backend (FastAPI :7777)
    │
    ├── main.py           → API endpoints
    ├── workflows/        → Claim adjudication workflow
    ├── agents/           → AI agents (5 total)
    └── database/         → SQLite storage
```

## Files Modified for Integration

1. **Created**:
   - `frontend/lib/api.ts` - API client service
   - `frontend/lib/types.ts` - TypeScript type definitions
   - `frontend/.env.local` - Environment configuration

2. **Updated**:
   - `frontend/app/page.tsx` - Real-time claim fetching
   - `frontend/app/submit/page.tsx` - API submission
   - `frontend/app/status/[id]/page.tsx` - Claim details from API
   - `frontend/app/appeal/page.tsx` - Appeal API integration
