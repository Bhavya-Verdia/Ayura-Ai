# 🧬 Ayura AI — AI-Powered Holistic Health Platform

**Ayura AI** is a one-stop holistic health web application that provides AI-driven, highly personalized health recommendations spanning modern fitness, traditional Ayurvedic practices, and natural healing.

## ✨ Features

- **🏋️ Gym Routines** — Personalized workout plans based on BMI, dosha, and fitness level
- **🧘 Yoga Plans** — Dosha-specific asana sequences with pranayama and meditation
- **🥗 Diet & Nutrition** — Ayurvedic + modern nutrition meal plans with macro tracking
- **🌿 Panchakarma Plans** — Personalized Ayurvedic detox protocols (home-adaptable)
- **💊 Home Remedies** — Symptom-matched natural remedies with safety filtering
- **🤖 AI Health Chatbot** — RAG-powered conversational health assistant
- **📋 Prakriti Quiz** — ML-powered dosha constitution analysis
- **🌞 Ritucharya** — Seasonal wellness auto-adjustments
- **📊 Progress Tracking** — Weight, symptoms, and adherence analytics with AI insights
- **📄 PDF Export** — Download plans for offline reference

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 (Vite) + Framer Motion + Recharts |
| Backend | Python 3.12 + FastAPI |
| Database | MongoDB 7 |
| Vector Database | ChromaDB |
| Logic | Rule-based engines |
| RAG Pipeline | LangChain + ChromaDB |
| LLM | Azure OpenAI GPT-4o / Google Gemini 2.0 Flash |
| Agentic AI | LangGraph (multi-agent orchestration) |
| Auth | JWT + Google OAuth 2.0 |

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- Docker Desktop

### 1. Start databases
```bash
docker-compose up -d
```

### 2. Setup backend
```bash
cd server
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp ../.env.example ../.env  # Edit with your API keys
python -m uvicorn main:app --reload --port 8000
```

### 3. Setup frontend
```bash
cd client
npm install
npm run dev
```

### 4. Seed data & build vectors
```bash
cd server/scripts
python build_vectors.py            # Load JSON knowledge base → ChromaDB
```

## 📁 Project Structure

```
Ayura AI/
├── client/          # React Frontend (Vite)
├── server/          # Python FastAPI Backend
│   ├── ai/          # GenAI + RAG + Agentic AI
│   ├── engine/      # Rule-based personalization
│   ├── models/      # Pydantic models for MongoDB
│   ├── routes/      # API endpoints
│   └── data/        # Knowledge base JSONs
├── scripts/         # Data seeding & vector building
└── docker-compose.yml
```

## ⚠️ Disclaimer

Ayura AI provides educational and informational content only. It is not a substitute for professional medical advice, diagnosis, or treatment. Always consult a qualified healthcare provider before making health decisions.
