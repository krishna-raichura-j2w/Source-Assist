import base64
import io
import json
import os
from datetime import date

from openai import AzureOpenAI
from pypdf import PdfReader

from .schema import EDUCATION_OPTIONS, EXPERIENCE_OPTIONS, ConsultantProfile

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_API_VERSION"),
)

DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

# USD per token for each known model. Falls back to gpt-4o-mini rates if unknown.
_MODEL_RATES: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.15  / 1_000_000, "output": 0.60  / 1_000_000},
    "gpt-4o":      {"input": 2.50  / 1_000_000, "output": 10.00 / 1_000_000},
    "gpt-4":       {"input": 30.00 / 1_000_000, "output": 60.00 / 1_000_000},
}


def calc_cost(model: str, input_tokens: int, output_tokens: int) -> tuple[float, float, float]:
    rates = _MODEL_RATES.get(model, _MODEL_RATES["gpt-4o-mini"])
    inp   = round(input_tokens  * rates["input"],  8)
    out   = round(output_tokens * rates["output"], 8)
    return inp, out, round(inp + out, 8)

SYSTEM_PROMPT = f"""You are an expert HR data extractor. Extract consultant profile information from the provided content.

Return a JSON object with ONLY these fields:
- sourcing_date: date profile was sourced (YYYY-MM-DD format; use today's date {date.today()} if not present)
- pool_verified: "Yes" or "No" — whether pool is verified by sourcing partner
- name: full name of the consultant
- mobile_number: the CANDIDATE'S personal mobile number only — see strict rules below
- email: email address
- linkedin_url: LinkedIn profile URL (use "N/A" if absent)
- education: must be one of {EDUCATION_OPTIONS} — pick closest match
- current_location: current city/location
- profile_active_naukri: "Yes" or "No" — whether profile is active on Naukri
- experience_range: must be one of {EXPERIENCE_OPTIONS} — pick closest match
- current_company: current employer/company where the candidate actively works. If anywhere in the resume it mentions the candidate is on payroll of a different company (e.g. "on payroll of ABC", "employed through ABC", "contract via ABC", "payrolled by ABC"), include the payroll company in brackets — e.g. "TCS (ABC)" where TCS is the working company and ABC is the payroll company. Search the entire resume for any such payroll or contract mention.
- relevant_skills: comma-separated list of skills
- immediate_joinee: "Yes" or "No" — whether candidate can join immediately

Rules:
- If information is not found, keep it empty
- profile_active_naukri - Keep it Yes
- education must always be mapped to one of the allowed options
- experience_range must always be mapped to one of the allowed options
- Return ONLY valid JSON with no markdown, code fences, or explanation
- Whether Immediate Joinee - If this information is not available, keep it empty.

Mobile number rules (strict):
- Extract ONLY the candidate's personal mobile/phone number — ignore company helplines, HR numbers, office landlines, or any number belonging to a recruiter or organisation
- The candidate's number is typically found near their name, email, or labelled "Mobile", "Ph", "Contact", "Cell"
- Output format: digits only, absolutely NO spaces, NO dashes, NO dots, NO brackets
- Include the + country code prefix ONLY if it is explicitly written in the source (e.g. +917678616930)
- If the number appears as "76786 16930" or "7678-616930" strip all separators and return "7678616930"
- If no candidate mobile number is found, return null
"""


def call_azure(content: list) -> tuple[ConsultantProfile, dict]:
    response = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": content},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    profile = ConsultantProfile(**json.loads(response.choices[0].message.content))
    usage   = response.usage
    inp, out, total = calc_cost(
        DEPLOYMENT,
        usage.prompt_tokens,
        usage.completion_tokens,
    )
    cost_info = {
        "model":           DEPLOYMENT,
        "input_tokens":    usage.prompt_tokens,
        "output_tokens":   usage.completion_tokens,
        "total_tokens":    usage.total_tokens,
        "input_cost_usd":  inp,
        "output_cost_usd": out,
        "total_cost_usd":  total,
    }
    return profile, cost_info


def image_block(img_bytes: bytes, mime: str) -> dict:
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}


def pdf_to_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
