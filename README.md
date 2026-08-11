# IntelliRepo

**Understand any public GitHub repository with AI.**

IntelliRepo is a full-stack SaaS application that helps developers analyze and understand GitHub repositories using AI-powered summaries and contextual chat. Paste a repository URL, and IntelliRepo clones it, indexes the source code, and generates a detailed, beginner-friendly explanation of how the project works.

![Dashboard Screenshot](./docs/screenshots/dashboard.png)
![Repository Overview Screenshot](./docs/screenshots/overview.png)
![Chat Screenshot](./docs/screenshots/chat.png)

> Placeholder paths — add screenshots after running the app locally.

---

## Features

- **Secure Authentication** — Register, login, and JWT-protected routes with bcrypt password hashing
- **Repository Analysis** — Clone public GitHub repos, read source files, and generate AI summaries
- **Detailed Overview** — Project summary, workflow explanation, architecture, important files, tech stack, and AI insights
- **RAG-Powered Chat** — Ask questions about the repository; answers come only from indexed code
- **Smart Caching** — Reuses embeddings when the same repository is analyzed again
- **Progress Tracking** — Visual step-by-step progress during analysis
- **Clean UI** — Modern, minimal, responsive design built for readability

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React, Vite, Tailwind CSS, React Router, Axios |
| **Backend** | Python, FastAPI |
| **Database** | MongoDB, PyMongo |
| **AI** | Google Gemini API, LangChain |
| **Vector Store** | ChromaDB |
| **Embeddings** | Sentence Transformers (all-MiniLM-L6-v2) |
| **Git** | GitPython |
| **Auth** | JWT, bcrypt |

---

## Architecture

```
IntelliRepo/
├── frontend/          # React SPA
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── layouts/
│   │   ├── context/
│   │   ├── services/
│   │   └── utils/
│   └── ...
└── backend/           # FastAPI API
    ├── api/
    ├── routes/
    ├── services/
    ├── auth/
    ├── database/
    ├── models/
    ├── schemas/
    ├── rag/
    ├── ai/
    ├── utils/
    └── repositories/
```

### Analysis Pipeline

```
GitHub URL → Validate → Clone (GitPython) → Read Source Files
    → Chunk (1000 / 200 overlap) → Embed (MiniLM) → Store (ChromaDB)
    → Generate Summary (Gemini) → Save Metadata (MongoDB)
```

### Chat Pipeline

```
User Question → Embed → Search ChromaDB → Retrieve Chunks
    → Combine with Summary → Gemini → Answer
```

---

## Installation

### Prerequisites

- **Node.js** 18+
- **Python** 3.10+
- **MongoDB** (local or Atlas)
- **Git** (for cloning repositories)
- **Google Gemini API Key** — [Get one here](https://aistudio.google.com/apikey)

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/intellirepo.git
cd intellirepo
```

### 2. Backend setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` with your credentials:

```env
GEMINI_API_KEY=your_gemini_api_key
JWT_SECRET=your_super_secret_jwt_key
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=IntelliRepo
GEMINI_MODEL=gemini-2.0-flash
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHROMA_DB_PATH=./chroma
```

### 3. Frontend setup

```bash
cd ../frontend
npm install
cp .env.example .env
```

---

## How to Run

Start MongoDB, then run both servers:

**Terminal 1 — Backend**

```bash
cd backend
venv\Scripts\activate   # or source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend**

```bash
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Environment Variables

### Backend

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Google Gemini API key |
| `JWT_SECRET` | Secret for signing JWT tokens |
| `MONGODB_URI` | MongoDB connection string |
| `DATABASE_NAME` | MongoDB database name |
| `GEMINI_MODEL` | Gemini model (default: `gemini-2.0-flash`) |
| `EMBEDDING_MODEL` | Sentence Transformers model |
| `CHROMA_DB_PATH` | Path for ChromaDB persistence |

### Frontend

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend API base URL |

---

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Register a new user |
| `POST` | `/api/auth/login` | Login and receive JWT |
| `GET` | `/api/auth/me` | Get current user (protected) |

### Repository

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/repository/analyze` | Analyze a GitHub repository |
| `GET` | `/api/repository` | List user's analyzed repositories |
| `GET` | `/api/repository/{id}` | Get repository details and summary |

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Send a message about a repository |

---

## MongoDB Collections

### Users

```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "<bcrypt hash>",
  "createdAt": "2026-01-01T00:00:00Z"
}
```

### Repositories

```json
{
  "userId": "<user id>",
  "repositoryName": "fastapi",
  "repositoryUrl": "https://github.com/tiangolo/fastapi",
  "owner": "tiangolo",
  "summary": { "...analysis JSON..." },
  "chromaCollection": "repo_tiangolo_fastapi",
  "createdAt": "2026-01-01T00:00:00Z"
}
```

---

## Future Improvements

- [ ] GitHub OAuth login
- [ ] Support for private repositories (with PAT)
- [ ] Streaming analysis progress via WebSockets
- [ ] Repository comparison view
- [ ] Export analysis as PDF/Markdown
- [ ] Team workspaces and shared analyses
- [ ] Rate limiting and usage quotas
- [ ] Docker Compose for one-command setup

---

## Coding Standards

- Modular folder structure with clear separation of concerns
- Business logic in services, not routes or components
- Meaningful variable and function names
- Comments only where they add clarity
- Consistent naming: `snake_case` (Python), `camelCase` (JavaScript)
- No placeholder or mock implementations for core features

---

## License

MIT
