import requests
import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, util

# Load env vars from .env file
load_dotenv()

model = SentenceTransformer('all-MiniLM-L6-v2')

JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY")
JSEARCH_ENDPOINT = "https://jsearch.p.rapidapi.com/search"

HEADERS = {
    "X-RapidAPI-Key": JSEARCH_API_KEY,
    "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
}

def fetch_jobs_from_api(query, num_results=10):
    params = {"query": query, "num_pages": 1}
    try:
        response = requests.get(JSEARCH_ENDPOINT, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Return the full job objects, not just descriptions
        jobs = data.get("data", [])[:num_results]
        print(f"✅ Retrieved {len(jobs)} job listings")  # Debugging
        return jobs

    except Exception as e:
        print(f"❌ API error: {e}")
        return []

def get_top_matches(resume_text, query, top_k=3):
    jobs = fetch_jobs_from_api(query)
    if not jobs:
        return []

    # Encode resume and job descriptions
    resume_embedding = model.encode(resume_text, convert_to_tensor=True)
    job_texts = [job.get("job_description", "") for job in jobs]
    job_embeddings = model.encode(job_texts, convert_to_tensor=True)
    
    similarities = util.pytorch_cos_sim(resume_embedding, job_embeddings)[0]
    top_results = similarities.argsort(descending=True)[:top_k]

    top_matches = []
    for idx in top_results:
        job = jobs[idx]
        # Truncate description for display (keep first 300 chars)
        full_description = job.get("job_description", "No description provided")
        short_description = (full_description[:300] + "...") if len(full_description) > 300 else full_description
        
        match = {
            "title": job.get("job_title", "No title"),
            "company": job.get("employer_name", "Unknown company"),
            "location": f"{job.get('job_city', '')}, {job.get('job_country', '')}".strip(", "),
            "description": short_description,
            "full_description": full_description,  # Include full description in case you need it later
            "score": round(float(similarities[idx]) * 100, 2),
            "apply_link": job.get("job_apply_link") or job.get("job_google_link") or "No link available",
            "posted_at": job.get("job_posted_at_datetime_utc", "Unknown date")
        }
        top_matches.append(match)

    return top_matches
