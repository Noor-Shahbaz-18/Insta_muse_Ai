<<<<<<< HEAD
# InstaMuse AI — Frontend (React + Vite + TypeScript + Tailwind)

## Run
```
npm install
cp .env.example .env      # already included
npm run dev               # http://localhost:5173
```
Starts in **Mock/Demo mode** (`VITE_USE_MOCK_API=true`), so the full flow works without a backend.

## Connect to the FastAPI backend
1. In `.env` set `VITE_USE_MOCK_API=false` and `VITE_API_BASE_URL=http://localhost:8000/api/v1`. Restart `npm run dev`.
2. Add CORS in FastAPI (`main.py`):
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])
```
3. Mount all routers under the `/api/v1` prefix. Errors must be `{"detail": "..."}`.
4. Test: open Settings or Dashboard. The header badge shows "Live API"; failures show "Cannot reach the backend".

## Where things live
- `src/api/client.ts` single Axios client + friendly error mapping (401/403/404/409/413/422/429/500)
- `src/api/services/index.ts` all 16 endpoints; the only place that switches mock/real
- `src/mocks/mockApi.ts` localStorage-backed mock with the same types
- `src/types/index.ts` shared contract types

## Pages and endpoints
| Page | Endpoints |
|---|---|
| Landing `/` | none |
| Dashboard `/dashboard` | GET /content, GET /security/status |
| AI Content Studio `/studio` | POST /media/upload, POST /content/generate, PATCH/approve/reject/publish/schedule |
| My Content `/content` | GET /content + same actions |
| Calendar `/calendar` | GET /content, POST /content/{id}/schedule |
| Security Guardian `/security` | GET /security/status, POST /security/scan, GET /security/alerts |
| Notifications `/notifications` | GET /notifications |
| Settings `/settings` | GET/PUT /business/profile |

## Notes
- Cancel schedule uses `PATCH /content/{id}` with `{status:"approved", scheduled_at:null}`; ask the backend dev to allow it, or add a dedicated endpoint.
- Not included yet: onboarding wizard, health check UI, month-grid calendar.
=======
# Insta_muse_Ai
>>>>>>> origin/main
