import os

ALLOWED_DOMAINS = {"joulestowatts.com", "joulestowatts.co"}

JWT_SECRET    = os.getenv("JWT_SECRET", "sourceassist-jwt-s3cr3t-2026-j2w")
JWT_ALGORITHM = "HS256"
JWT_DAYS      = 30
