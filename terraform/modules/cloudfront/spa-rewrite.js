// Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
// Purpose: Implements edge request processing used by the cloudfront Terraform module.
// The handler comments explain how requests are classified and rewritten.

function handler(event) {
  var request = event.request;
  var uri = request.uri;
  var leaf = uri.substring(uri.lastIndexOf('/') + 1);
  // Preserve API, file, and already-qualified paths; rewrite only client-side SPA routes.
  if (uri.endsWith('/') || !leaf.includes('.')) {
    request.uri = '/index.html';
  }
  return request;
}
