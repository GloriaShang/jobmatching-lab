// Vercel Serverless Function
// Deployed URL will look like: https://<your-project>.vercel.app/api/classify
// Normalizes a free-text major name into one of the six project categories.
const categories = ['Engineering', 'Science', 'Business', 'Humanities', 'Agriculture', 'Other'];

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, x-app-token');

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  if (req.method === 'GET') {
    res.status(200).json({
      status: 'ok',
      message: 'This endpoint is live. Call it with POST and a JSON body like {"majorName": "机电一体化技术"}.',
    });
    return;
  }

  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Only GET (health check) and POST are supported.' });
    return;
  }

  const appSecret = process.env.APP_SECRET;
  if (appSecret) {
    const provided = req.headers['x-app-token'];
    if (provided !== appSecret) {
      res.status(401).json({ error: 'Missing or incorrect x-app-token header.' });
      return;
    }
  }

  const input = req.body?.majorName;
  const majorName = typeof input === 'string' ? input.trim() : '';
  if (!majorName) {
    res.status(400).json({ error: 'Request body must include a non-empty "majorName" string.' });
    return;
  }

  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    res.status(500).json({ error: 'Server is missing the GEMINI_API_KEY environment variable.' });
    return;
  }

  const model = process.env.GEMINI_MODEL || 'gemini-3.5-flash-lite';
  const instruction =
    'Classify a higher-education program name into one of these categories: ' +
    `${categories.join(', ')}. Use Other when the category is unclear.`;

  try {
    const upstream = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-goog-api-key': apiKey },
        signal: AbortSignal.timeout(10000),
        body: JSON.stringify({
          systemInstruction: { parts: [{ text: instruction }] },
          contents: [{ parts: [{ text: majorName }] }],
          generationConfig: {
            maxOutputTokens: 128,
            responseMimeType: 'application/json',
            responseSchema: {
              type: 'OBJECT',
              properties: { category: { type: 'STRING', enum: categories } },
              required: ['category'],
            },
          },
        }),
      }
    );

    if (!upstream.ok) {
      res.status(upstream.status).json({ error: 'Gemini API error' });
      return;
    }

    const data = await upstream.json();
    const content = data?.candidates?.[0]?.content?.parts
      ?.filter(part => !part.thought && typeof part.text === 'string')
      .map(part => part.text)
      .join('');
    const category = content ? JSON.parse(content)?.category : undefined;
    if (!categories.includes(category)) {
      res.status(502).json({ error: 'Gemini returned no valid category.' });
      return;
    }

    res.status(200).json({ majorName, category });
  } catch {
    res.status(502).json({ error: 'Request to Gemini API failed' });
  }
}
