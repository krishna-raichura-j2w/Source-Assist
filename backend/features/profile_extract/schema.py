from typing import Optional

from pydantic import BaseModel

EDUCATION_OPTIONS = [
    "B.Tech / BE", "M.Tech / ME", "BCA", "MCA",
    "B.Sc", "M.Sc", "B.Com", "MBA", "Diploma", "PhD", "Other",
]

EXPERIENCE_OPTIONS = [
    "0-1 yr", "1-3 yrs", "3-5 yrs", "5-8 yrs",
    "8-12 yrs", "12-15 yrs", "15+ yrs",
]


class ConsultantProfile(BaseModel):
    sourcing_date:         Optional[str] = None
    pool_verified:         Optional[str] = None
    name:                  Optional[str] = None
    mobile_number:         Optional[str] = None
    email:                 Optional[str] = None
    linkedin_url:          Optional[str] = None
    education:             Optional[str] = None
    current_location:      Optional[str] = None
    profile_active_naukri: Optional[str] = None
    experience_range:      Optional[str] = None
    current_company:       Optional[str] = None
    relevant_skills:       Optional[str] = None
    immediate_joinee:      Optional[str] = None
