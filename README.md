# UofT Syllabus Assistant 🎓

An AI-powered chatbot that helps University of Toronto students get instant answers from course syllabus using RAG (Retrieval-Augmented Generation).

**Live Demo**: [http://3.140.6.205/](http://3.140.6.205/)

## 💬 Try These Sample Questions

```
"What is the grading scheme for MAT235?"
"When are the office hours for STA237?"
"What are the prerequisites for MAT224?"
"What topics are covered in week 5 of MAT235?"
"How is the final exam weighted in STA237?"
"What textbook is required for MAT224?"
"Tell me about the late submission policy"
```

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

