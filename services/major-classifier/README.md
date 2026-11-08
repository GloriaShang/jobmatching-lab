# Major classifier · 专业名称标准化

This optional API maps a typed major or program name to one of six categories used by JobMatching Lab. Employment-service staff can use the result as a suggested label when preparing records for referral review. The model receives only the major name. Use only that field and review ambiguous classifications before using them downstream. The dashboard and Python experiments run independently of this service.

这个可选接口把自由填写的专业名称归到六个类别之一，供就业服务人员在整理转介资料时复核。接口只接收专业名称。公开看板和 Python 实验可以独立运行。

## API

- `GET /api/classify` checks that the route is reachable.
- `POST /api/classify` accepts a JSON object with a non-empty `majorName` string.
- Success returns the trimmed `majorName` and one `category` from `Engineering`, `Science`, `Business`, `Humanities`, `Agriculture` and `Other`. An unavailable or invalid upstream response yields an error.

## Run the offline tests

From this directory with Node.js 22 or later:

```bash
npm test
```

The tests mock the Gemini request and run without installing dependencies or using credentials.

## Deploy on Vercel

Import `GloriaShang/jobmatching-lab` into Vercel and set its **Root Directory** to `services/major-classifier`. Select the **Other** framework preset and a supported Node.js runtime at or above version 22. Set these environment variables for the service deployment:

| Variable | Value |
| --- | --- |
| `GEMINI_API_KEY` | Server-side Gemini API key |
| `APP_SECRET` | Shared token for trusted callers. Set it when deploying to a reachable URL. |
| `GEMINI_MODEL` | Optional override for a Gemini model that supports structured output. The default is `gemini-3.5-flash-lite`. |

Keep both credentials on the server or in trusted caller environments. Deploy and substitute your Vercel project URL below. A POST makes a request to Gemini.

```bash
curl https://YOUR-PROJECT.vercel.app/api/classify
curl --fail-with-body https://YOUR-PROJECT.vercel.app/api/classify \
  -H 'Content-Type: application/json' \
  -H "x-app-token: $APP_SECRET" \
  -d '{"majorName":"机电一体化技术"}'
```

Example response:

```json
{"majorName":"机电一体化技术","category":"Engineering"}
```

The original endpoint is from [GloriaShang/JobMatching-backend at commit 73c58d4](https://github.com/GloriaShang/JobMatching-backend/commit/73c58d46b07dab3b31a3679135bfbf29b073cac5). The consolidated copy uses the same public route and success fields, with a current default model for new projects and a constrained output schema. [Gemini model catalog](https://ai.google.dev/gemini-api/docs/models)
