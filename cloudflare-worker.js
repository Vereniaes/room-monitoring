// Cloudflare Worker — proxy HTTP/1.1 dari Wokwi ke Cloud Run
// Deploy di: https://dash.cloudflare.com/workers
// 
// Wokwi → (HTTPS ke Cloudflare, h2-compatible) → Worker → Cloud Run
//
// Cara deploy:
// 1. Buka https://dash.cloudflare.com
// 2. Klik Workers & Pages → Create Application → Create Worker
// 3. Paste kode ini → Save & Deploy
// 4. Copy URL worker (misal: iot-proxy.username.workers.dev)
// 5. Update GATEWAY_URL di main_secure.py

const CLOUD_RUN_URL = "https://room-monitoring-476404504908.asia-southeast2.run.app"

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url)

    // Forward path + query ke Cloud Run
    const targetUrl = CLOUD_RUN_URL + url.pathname + url.search

    // Clone request ke Cloud Run
    const newRequest = new Request(targetUrl, {
      method:  request.method,
      headers: request.headers,
      body:    request.method !== "GET" && request.method !== "HEAD"
               ? request.body
               : undefined
    })

    try {
      const response = await fetch(newRequest)

      // Kembalikan response ke Wokwi
      const newResponse = new Response(response.body, {
        status:     response.status,
        statusText: response.statusText,
        headers:    response.headers
      })
      newResponse.headers.set("Access-Control-Allow-Origin", "*")
      return newResponse

    } catch (err) {
      return new Response(JSON.stringify({ error: err.message }), {
        status: 500,
        headers: { "Content-Type": "application/json" }
      })
    }
  }
}
