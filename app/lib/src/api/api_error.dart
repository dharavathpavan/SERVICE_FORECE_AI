import 'package:dio/dio.dart';

/// Typed API failures. Every variant carries a message safe to show a user, so
/// widgets never have to render a raw exception string.
sealed class ApiError implements Exception {
  const ApiError(this.userMessage, {this.statusCode, this.details});

  final String userMessage;
  final int? statusCode;
  final Object? details;

  /// Whether retrying the same request could plausibly succeed.
  bool get retryable => false;

  @override
  String toString() => userMessage;

  static ApiError fromDio(DioException e) {
    final Response<dynamic>? response = e.response;
    final int? status = response?.statusCode;

    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.transformTimeout:
        return const NetworkError(
            'The request timed out. Check your connection and try again.');
      case DioExceptionType.connectionError:
        return const NetworkError(
            'Cannot reach the server. Is the backend running?');
      case DioExceptionType.cancel:
        return const CancelledError();
      case DioExceptionType.badCertificate:
        return const NetworkError(
            'The server certificate could not be verified.');
      case DioExceptionType.badResponse:
      case DioExceptionType.unknown:
        break;
    }

    final String detail = _extractDetail(response?.data);
    switch (status) {
      case 400:
        return ValidationError(
            detail.isEmpty ? 'The request was invalid.' : detail,
            details: response?.data);
      case 401:
        return const AuthError(
            'Your session has expired. Please sign in again.');
      case 403:
        return ForbiddenError(
            detail.isEmpty ? 'You do not have permission to do that.' : detail);
      case 404:
        return NotFoundError(
            detail.isEmpty ? 'That item could not be found.' : detail);
      case 409:
        return ConflictError(detail.isEmpty
            ? 'That action conflicts with the current state.'
            : detail);
      case 422:
        return ValidationError(
            detail.isEmpty ? 'Some fields need attention.' : detail,
            details: response?.data);
      default:
        if (status != null && status >= 500) {
          return ServerError(
            'The server had a problem. Please try again shortly.',
            statusCode: status,
            details: response?.data,
          );
        }
        if (status == 429) {
          return NetworkError(
            'Too many requests right now. Wait a moment and try again.',
            statusCode: status,
            details: response?.data,
          );
        }
        if (status != null) {
          // An unhandled 4xx. Repeating the identical request will not help, so
          // this must not be reported as a retryable network failure.
          return UnexpectedError(
            detail.isEmpty
                ? 'The request was rejected (HTTP $status).'
                : detail,
            statusCode: status,
            details: response?.data,
          );
        }
        return NetworkError(
            detail.isEmpty ? 'Something went wrong. Please try again.' : detail,
            details: response?.data);
    }
  }

  static String _extractDetail(Object? data) {
    if (data is Map<dynamic, dynamic>) {
      final Object? detail = data['detail'] ?? data['message'];
      if (detail is String) return detail;
      if (detail is List<dynamic> && detail.isNotEmpty) {
        final Object? first = detail.first;
        if (first is Map<dynamic, dynamic> && first['msg'] is String) {
          return first['msg'] as String;
        }
        return detail.join(', ');
      }
    }
    if (data is String) return data;
    return '';
  }
}

class NetworkError extends ApiError {
  const NetworkError(super.userMessage, {super.statusCode, super.details});

  @override
  bool get retryable => true;
}

class AuthError extends ApiError {
  const AuthError(super.userMessage, {super.statusCode, super.details});
}

class ForbiddenError extends ApiError {
  const ForbiddenError(super.userMessage, {super.statusCode, super.details});
}

class NotFoundError extends ApiError {
  const NotFoundError(super.userMessage, {super.statusCode, super.details});
}

class ConflictError extends ApiError {
  const ConflictError(super.userMessage, {super.statusCode, super.details});
}

class ValidationError extends ApiError {
  const ValidationError(super.userMessage, {super.statusCode, super.details});
}

/// A well-formed response the client did not expect (an unhandled 4xx).
class UnexpectedError extends ApiError {
  const UnexpectedError(super.userMessage, {super.statusCode, super.details});
}

class ServerError extends ApiError {
  const ServerError(super.userMessage, {super.statusCode, super.details});

  @override
  bool get retryable => true;
}

class CancelledError extends ApiError {
  const CancelledError() : super('The request was cancelled.');

  @override
  bool get retryable => true;
}
