# UofT Course Assistant 🎓

An AI-powered chatbot that helps University of Toronto students get instant answers from course syllabi using RAG (Retrieval-Augmented Generation).

**Live Demo**: [http://3.140.6.205/static/index.html](http://3.140.6.205/static/index.html)

## ✨ Key Features

- 🤖 **RAG Architecture**: Combines vector search with LLM for accurate, context-aware answers
- 📚 **Multi-Course Support**: Query information across multiple course documents
- ⚡ **Fast**: Powered by GROQ's ultra-fast LLM inference
- 💾 **Conversation History**: Auto-saves chat history in browser
- 🚀 **Auto-Deploy**: CI/CD pipeline with GitHub Actions → AWS EC2

## 🛠️ Tech Stack

**Backend**:
- FastAPI + LangChain
- GROQ API (llama-3.3-70b-versatile)
- ChromaDB (vector database)
- sentence-transformers (embeddings)

**Infrastructure**:
- AWS EC2 + Nginx
- GitHub Actions (CI/CD)
- systemd (process management)

## 🚀 Quick Start

```bash
# 1. Clone and install
git clone https://github.com/YOUR_USERNAME/uoft-assistant.git
cd uoft-assistant
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure .env
cp .env.example .env
# Add your GROQ_API_KEY

# 3. Run
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Visit [http://localhost:8000/static/index.html](http://localhost:8000/static/index.html)

## 📁 Project Structure

```
app/
├── main.py           # FastAPI app
├── rag_service.py    # RAG logic + ChromaDB
├── middleware.py     # Auth + rate limiting
static/
├── index.html        # Chat UI
└── js/app.js         # Frontend logic
.github/workflows/
└── deploy.yml        # CI/CD pipeline
```

## 🔌 API Example

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the grading scheme for MAT235?"}'
```

## 🚢 Deployment

Push to `main` branch → GitHub Actions automatically deploys to AWS EC2

```bash
git push origin main
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for setup details.

## 📝 License

MIT License - See [LICENSE](LICENSE) file

---
