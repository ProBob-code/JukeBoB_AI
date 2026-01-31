/// Environment configuration for backend API
class EnvConfig {
  static final String backendBaseUrl = const String.fromEnvironment(
    'BACKEND_BASE_URL',
    defaultValue: 'http://localhost:5000',
  );

  static Uri api(String path) {
    final base = backendBaseUrl.endsWith('/')
        ? backendBaseUrl.substring(0, backendBaseUrl.length - 1)
        : backendBaseUrl;
    final p = path.startsWith('/') ? path : '/$path';
    return Uri.parse('$base$p');
  }

  static Uri ws(String path) {
    final baseUri = Uri.parse(backendBaseUrl);
    final p = path.startsWith('/') ? path : '/$path';
    final scheme = (baseUri.scheme == 'https') ? 'wss' : 'ws';
    final combinedPath = (baseUri.path == '/' || baseUri.path.isEmpty)
        ? p
        : ('${baseUri.path}$p');
    return Uri(
        scheme: scheme,
        host: baseUri.host,
        port: baseUri.hasPort ? baseUri.port : null,
        path: combinedPath);
  }
}
