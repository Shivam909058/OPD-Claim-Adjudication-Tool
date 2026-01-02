# OPD Claim Adjudication Tool

AI-powered system for automating OPD (Outpatient Department) insurance claim adjudication using the Agno AI Framework.

## 🚀 Features

- **AI-Powered Document Extraction**: Uses LLMs to extract data from medical documents
- **Multi-Agent Workflow**: 5 specialized agents working together
- **Rule-Based + AI Decisions**: Combines deterministic rules with AI reasoning
- **Fraud Detection**: Identifies suspicious claim patterns
- **RESTful API**: Easy integration with any frontend
- **Confidence Scoring**: Every decision includes a confidence score

## 📋 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Claim Submission                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 ADJUDICATION WORKFLOW                        │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐ │
│  │ Document  │─▶│Eligibility│─▶│ Coverage  │─▶│  Limit    │ │
│  │ Extractor │  │  Checker  │  │ Validator │  │Calculator │ │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘ │
│                                                      │       │
│                                                      ▼       │
│                                               ┌───────────┐  │
│                                               │ Decision  │  │
│                                               │  Maker    │  │
│                                               └───────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│     APPROVED / REJECTED / PARTIAL / MANUAL_REVIEW            │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ Tech Stack

- **Backend**: Python + FastAPI
- **AI Framework**: Agno
- **LLM**: OpenAI GPT-4o-mini
- **Database**: SQLite (easily swappable to PostgreSQL)
- **Validation**: Pydantic v2

## 📦 Installation

### 1. Clone and Setup

```bash
cd opd_verify_tool
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file with your API key:

```env
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=sqlite:///./opd_claims.db
HOST=0.0.0.0
PORT=7777
DEBUG=true
```

### 4. Run the Server

```bash
python -m app.main
# OR
uvicorn app.main:app --reload --port 7777
```

The API will be available at `http://localhost:7777`

## 📖 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:7777/docs
- **ReDoc**: http://localhost:7777/redoc

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/claims/submit` | Submit a new claim |
| GET | `/api/claims/{claim_id}` | Get claim details |
| GET | `/api/claims` | List all claims |
| POST | `/api/claims/{claim_id}/appeal` | Submit an appeal |
| GET | `/api/policy/terms` | Get policy terms |

### Example: Submit a Claim

```bash
curl -X POST http://localhost:7777/api/claims/submit \
  -H "Content-Type: application/json" \
  -d '{
    "member_id": "EMP001",
    "member_name": "Rajesh Kumar",
    "treatment_date": "2024-11-01",
    "claim_amount": 1500,
    "documents": {
      "prescription": {
        "doctor_name": "Dr. Sharma",
        "doctor_reg": "KA/45678/2015",
        "diagnosis": "Viral fever",
        "medicines_prescribed": ["Paracetamol 650mg"]
      },
      "bill": {
        "consultation_fee": 1000,
        "diagnostic_tests": 500
      }
    }
  }'
```

## 🧪 Testing

Run the test suite:

```bash
python test_claims.py
```

## 📁 Project Structure

```
opd_verify_tool/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Configuration settings
│   │
│   ├── agents/              # Agno AI Agents
│   │   ├── document_extractor.py
│   │   ├── eligibility_checker.py
│   │   ├── coverage_validator.py
│   │   ├── limit_calculator.py
│   │   └── decision_maker.py
│   │
│   ├── workflows/           # Agno Workflows
│   │   └── claim_adjudication.py
│   │
│   ├── tools/               # Helper tools
│   │   ├── policy_tools.py
│   │   └── fraud_detection.py
│   │
│   ├── models/              # Pydantic models
│   │   ├── claim.py
│   │   └── decision.py
│   │
│   └── database/            # Database setup
│       └── db.py
│
├── docs/                    # Documentation & policy files
│   ├── policy_terms.json
│   └── adjudication_rules.md
│
├── requirements.txt
├── .env
└── README.md
```

## 🎯 Decision Logic

The system makes decisions based on:

1. **Eligibility** - Policy active, waiting period satisfied
2. **Coverage** - Treatment covered, not in exclusions
3. **Limits** - Within per-claim (₹5,000) and annual (₹50,000) limits
4. **Fraud** - No suspicious patterns detected

### Decision Outcomes

- **APPROVED**: All checks pass
- **REJECTED**: Hard failure (policy issues, exclusions, limits exceeded)
- **PARTIAL**: Some items covered, some excluded
- **MANUAL_REVIEW**: Needs human review (fraud indicators, low confidence)

## 🔑 Policy Rules

| Rule | Value |
|------|-------|
| Per-Claim Limit | ₹5,000 |
| Annual Limit | ₹50,000 |
| Consultation Co-pay | 10% |
| Initial Waiting | 30 days |
| Diabetes Waiting | 90 days |
| Minimum Claim | ₹500 |

## 🚧 Future Improvements

- [ ] OCR integration for actual document processing
- [ ] Admin dashboard for policy configuration
- [ ] Email notifications
- [ ] Analytics and reporting
- [ ] Multi-language support
- [ ] Audit logging

## � Deployment on Render

### Option 1: One-Click Deploy with Blueprint

1. Push your code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click **New** → **Blueprint**
4. Connect your GitHub repo
5. Render will detect `render.yaml` and create both services

### Option 2: Manual Deployment

#### Deploy Backend (FastAPI)

1. Go to Render Dashboard → **New** → **Web Service**
2. Connect your GitHub repo
3. Configure:
   - **Name**: `opd-claims-api`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add Environment Variable:
   - `OPENAI_API_KEY` = your OpenAI key
5. Deploy!

#### Deploy Frontend (Next.js)

1. Go to Render Dashboard → **New** → **Web Service**
2. Connect your GitHub repo
3. Configure:
   - **Name**: `opd-claims-frontend`
   - **Runtime**: Node
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Start Command**: `npm start`
4. Add Environment Variable:
   - `NEXT_PUBLIC_API_URL` = `https://opd-claims-api.onrender.com` (your backend URL)
5. Deploy!

### Environment Variables

| Variable | Service | Value |
|----------|---------|-------|
| `OPENAI_API_KEY` | Backend | Your OpenAI API key |
| `NEXT_PUBLIC_API_URL` | Frontend | Backend URL (e.g., `https://opd-claims-api.onrender.com`) |

## �📄 License

MIT License

---

Built with ❤️ for Plum Health Insurance
