import 'dart:async';

import 'package:dio/dio.dart';

import 'api_error.dart';

/// Base URL of the ServiceForce API. Override at build time:
/// `flutter build web --dart-define=API_BASE_URL=https://api.example.com/api/v1`
const String kApiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://localhost:8000/api/v1',
);

/// WebSocket base derived from the API base (http -> ws).
String wsBaseUrl() {
  final Uri uri = Uri.parse(kApiBaseUrl);
  final String scheme = uri.scheme == 'https' ? 'wss' : 'ws';
  return '$scheme://${uri.authority}${uri.path}';
}

/// Supplies the current auth token and active organization. Implemented by the
/// auth controller; keeps this client free of state-management concerns.
abstract interface class TokenProvider {
  String? get accessToken;
  String? get organizationId;
  Future<void> onUnauthorized();
}

/// Thin, typed wrapper over Dio.
///
/// Responsibilities: base URL, auth headers, tenant header, and converting every
/// failure into an [ApiError]. It never leaks DioException to callers.
class ApiClient {
  ApiClient({Dio? dio, required TokenProvider tokens})
      : _tokens = tokens,
        _dio = dio ??
            Dio(
              BaseOptions(
                baseUrl: kApiBaseUrl,
                connectTimeout: const Duration(seconds: 10),
                receiveTimeout: const Duration(seconds: 30),
                sendTimeout: const Duration(seconds: 20),
                contentType: Headers.jsonContentType,
                headers: <String, String>{'Accept': 'application/json'},
              ),
            ) {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (RequestOptions options, RequestInterceptorHandler handler) {
          final String? token = _tokens.accessToken;
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          final String? orgId = _tokens.organizationId;
          if (orgId != null && orgId.isNotEmpty) {
            options.headers['X-Organization-Id'] = orgId;
          }
          handler.next(options);
        },
        onError: (DioException e, ErrorInterceptorHandler handler) {
          final ApiError error = ApiError.fromDio(e);
          if (error is AuthError) {
            // Fire and forget: the controller handles redirect + cleanup.
            unawaited(_tokens.onUnauthorized());
          }
          handler.next(e.copyWith(error: error));
        },
      ),
    );
  }

  final Dio _dio;
  final TokenProvider _tokens;

  Dio get raw => _dio;

  Future<T> _guard<T>(Future<T> Function() run) async {
    try {
      return await run();
    } on DioException catch (e) {
      final Object? err = e.error;
      throw err is ApiError ? err : ApiError.fromDio(e);
    }
  }

  Future<Map<String, dynamic>> getJson(
    String path, {
    Map<String, dynamic>? query,
  }) async {
    return _guard(() async {
      final Response<dynamic> r =
          await _dio.get<dynamic>(path, queryParameters: query);
      return _asMap(r.data);
    });
  }

  Future<List<dynamic>> getList(
    String path, {
    Map<String, dynamic>? query,
  }) async {
    return _guard(() async {
      final Response<dynamic> r =
          await _dio.get<dynamic>(path, queryParameters: query);
      final Object? data = r.data;
      if (data is List<dynamic>) return data;
      if (data is Map<dynamic, dynamic> && data['items'] is List<dynamic>) {
        return data['items'] as List<dynamic>;
      }
      return <dynamic>[];
    });
  }

  Future<Map<String, dynamic>> postJson(
    String path, {
    Object? body,
    Map<String, dynamic>? query,
  }) async {
    return _guard(() async {
      final Response<dynamic> r =
          await _dio.post<dynamic>(path, data: body, queryParameters: query);
      return _asMap(r.data);
    });
  }

  Future<List<dynamic>> postList(
    String path, {
    Object? body,
    Map<String, dynamic>? query,
  }) async {
    return _guard(() async {
      final Response<dynamic> r =
          await _dio.post<dynamic>(path, data: body, queryParameters: query);
      final Object? data = r.data;
      if (data is List<dynamic>) return data;
      return <dynamic>[];
    });
  }

  Future<Map<String, dynamic>> patchJson(String path, {Object? body}) async {
    return _guard(() async {
      final Response<dynamic> r = await _dio.patch<dynamic>(path, data: body);
      return _asMap(r.data);
    });
  }

  Future<void> delete(String path) async {
    return _guard(() async {
      await _dio.delete<dynamic>(path);
    });
  }

  /// Fetches a binary response (audio, exports) with auth applied.
  Future<List<int>> getBytes(String path) async {
    return _guard(() async {
      final Response<List<int>> r = await _dio.get<List<int>>(
        path,
        options: Options(responseType: ResponseType.bytes),
      );
      return r.data ?? <int>[];
    });
  }

  /// Form-encoded POST, used by the OAuth2 password token endpoint.
  Future<Map<String, dynamic>> postForm(
      String path, Map<String, dynamic> fields) async {
    return _guard(() async {
      final Response<dynamic> r = await _dio.post<dynamic>(
        path,
        data: FormData.fromMap(fields),
        options: Options(contentType: 'application/x-www-form-urlencoded'),
      );
      return _asMap(r.data);
    });
  }

  static Map<String, dynamic> _asMap(Object? data) {
    if (data is Map<String, dynamic>) return data;
    if (data is Map<dynamic, dynamic>) return data.cast<String, dynamic>();
    return <String, dynamic>{};
  }
}

/// Helpers for reading loosely-typed JSON safely.
extension JsonRead on Map<String, dynamic> {
  String? optString(String key) {
    final Object? v = this[key];
    if (v == null) return null;
    return v is String ? v : v.toString();
  }

  String str(String key, {String fallback = ''}) => optString(key) ?? fallback;

  int intOr(String key, int fallback) {
    final Object? v = this[key];
    if (v is int) return v;
    if (v is num) return v.toInt();
    if (v is String) return int.tryParse(v) ?? fallback;
    return fallback;
  }

  double doubleOr(String key, double fallback) {
    final Object? v = this[key];
    if (v is num) return v.toDouble();
    if (v is String) return double.tryParse(v) ?? fallback;
    return fallback;
  }

  bool boolOr(String key, bool fallback) {
    final Object? v = this[key];
    if (v is bool) return v;
    if (v is String) return v.toLowerCase() == 'true';
    if (v is num) return v != 0;
    return fallback;
  }

  DateTime? dateOrNull(String key) {
    final Object? v = this[key];
    if (v is String && v.isNotEmpty) return DateTime.tryParse(v)?.toLocal();
    return null;
  }

  Map<String, dynamic> mapOr(String key) {
    final Object? v = this[key];
    if (v is Map<String, dynamic>) return v;
    if (v is Map<dynamic, dynamic>) return v.cast<String, dynamic>();
    return <String, dynamic>{};
  }

  List<Map<String, dynamic>> listOfMaps(String key) {
    final Object? v = this[key];
    if (v is List<dynamic>) {
      return v
          .whereType<Map<dynamic, dynamic>>()
          .map((Map<dynamic, dynamic> m) => m.cast<String, dynamic>())
          .toList();
    }
    return <Map<String, dynamic>>[];
  }
}
