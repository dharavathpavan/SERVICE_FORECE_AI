import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:serviceforce/src/api/api_error.dart';

/// These tests cover the error-classification layer. They are pure Dart, so they
/// run without a device or browser.

DioException _response(int status, {Object? body}) {
  final RequestOptions options = RequestOptions(path: '/calls/outbound');
  return DioException(
    requestOptions: options,
    type: DioExceptionType.badResponse,
    response: Response<dynamic>(
      requestOptions: options,
      statusCode: status,
      data: body,
    ),
  );
}

void main() {
  group('ApiError.fromDio', () {
    test('maps 401 to AuthError', () {
      final ApiError error = ApiError.fromDio(_response(401));
      expect(error, isA<AuthError>());
      expect(error.userMessage, contains('session'));
    });

    test('maps 403 with detail to ForbiddenError carrying the detail', () {
      final ApiError error = ApiError.fromDio(
        _response(
          403,
          body: <String, dynamic>{
            'detail': 'Only Owners can remove another Owner',
          },
        ),
      );
      expect(error, isA<ForbiddenError>());
      expect(error.userMessage, 'Only Owners can remove another Owner');
    });

    test('maps 409 to ConflictError', () {
      expect(ApiError.fromDio(_response(409)), isA<ConflictError>());
    });

    test(
        'maps 422 validation lists to a ValidationError with the first message',
        () {
      final ApiError error = ApiError.fromDio(
        _response(
          422,
          body: <String, dynamic>{
            'detail': <dynamic>[
              <String, dynamic>{'msg': 'phone_number is required'},
            ],
          },
        ),
      );
      expect(error, isA<ValidationError>());
      expect(error.userMessage, 'phone_number is required');
    });

    test(
        'maps 500 to a retryable ServerError and keeps the body for inspection',
        () {
      final ApiError error = ApiError.fromDio(
        _response(
          503,
          body: <String, dynamic>{
            'status': 'not_ready',
            'checks': <String, dynamic>{'database': 'connected'},
          },
        ),
      );
      expect(error, isA<ServerError>());
      expect(error.retryable, isTrue);
      expect((error.details! as Map<dynamic, dynamic>)['status'], 'not_ready');
    });

    test('maps connection failures to a retryable NetworkError', () {
      final ApiError error = ApiError.fromDio(
        DioException(
          requestOptions: RequestOptions(path: '/health'),
          type: DioExceptionType.connectionError,
        ),
      );
      expect(error, isA<NetworkError>());
      expect(error.retryable, isTrue);
    });

    test('never exposes an exception string to the user', () {
      final ApiError error = ApiError.fromDio(_response(418));
      expect(error.userMessage, isNotEmpty);
      expect(error.userMessage, isNot(contains('DioException')));
      expect(error.retryable, isFalse);
    });
  });
}
