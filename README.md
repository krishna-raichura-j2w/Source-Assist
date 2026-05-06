# SourceAssist Backend

## Environment Variables

Create a `.env` file in the project root with the values your backend needs:

```env
SUPABASE_DB_URL=
JWT_SECRET=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_API_VERSION=
AZURE_OPENAI_DEPLOYMENT=
GMAIL_USER=
GMAIL_APP_PASSWORD=
FROM_EMAIL=
SMTP_HOST=
SMTP_PORT=
SMTP_USERNAME=
SMTP_PASSWORD=
```

## Start the Backend

```bash
uvicorn app:app --reload
```
