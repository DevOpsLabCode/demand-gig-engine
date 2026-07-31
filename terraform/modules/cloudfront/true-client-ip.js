// Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
// Purpose: Overwrites a private origin header with CloudFront's authenticated viewer IP so regional WAF rate limits cannot trust a spoofed X-Forwarded-For value.
async function handler(event) {
  var request = event.request;
  request.headers["x-origin-viewer-ip"] = { value: event.viewer.ip };
  return request;
}
