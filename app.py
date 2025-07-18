# app.py
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from matcher import get_top_matches
import fitz  # PyMuPDF
import io
import requests
import os

app = FastAPI()

# Allow frontend to connect (CORS setup)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_text_from_pdf(uploaded_file: UploadFile) -> str:
    """Extracts text from a PDF file using PyMuPDF"""
    try:
        pdf_data = uploaded_file.file.read()
        pdf_stream = io.BytesIO(pdf_data)
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"
    

# Remove the dummy fetch_jobs_from_api function entirely

@app.post("/match-jobs/")
async def match_jobs(file: UploadFile = File(...), query: str = Form(...)):
    if not file.filename.endswith(".pdf"):
        return {"error": "Please upload a PDF file."}

    resume_text = extract_text_from_pdf(file)
    
    if not resume_text or "Error" in resume_text:
        return {"error": "Failed to extract text from resume."}

    try:
        top_matches = get_top_matches(resume_text, query=query, top_k=3)
        return {"matches": top_matches}
    except Exception as e:
        return {"error": f"Job matching failed: {str(e)}"}


# ✅ NEW: Fetch live jobs using JSearch API
@app.get("/get-jobs/")
async def get_jobs(query: str = Query(..., description="Job search keyword")):
    api_key = os.getenv("JSEARCH_API_KEY")
    if not api_key:
        return {"error": "JSEARCH_API_KEY not set in environment."}

    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    params = {"query": query, "num_pages": 1}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        results = response.json().get("data", [])

        jobs = []
        for job in results:
            jobs.append({
                "title": job.get("job_title"),
                "company": job.get("employer_name"),
                "location": job.get("job_city"),
                "description": job.get("job_description", "")[:300] + "...",
                "apply_link": job.get("job_apply_link")
            })

        return {"jobs": jobs}
    
    except Exception as e:
        return {"error": f"Failed to fetch jobs: {str(e)}"}
