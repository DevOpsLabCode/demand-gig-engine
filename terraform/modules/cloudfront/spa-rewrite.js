function handler(event) {
  var request = event.request;
  var uri = request.uri;
  var leaf = uri.substring(uri.lastIndexOf('/') + 1);
  if (uri.endsWith('/') || !leaf.includes('.')) {
    request.uri = '/index.html';
  }
  return request;
}
