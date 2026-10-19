import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

import '../api/api_client.dart';

/// One message from the live call stream.
class CallStreamEvent {
  const CallStreamEvent({
    required this.eventType,
    required this.payload,
    required this.replay,
    required this.receivedAt,
  });

  final String eventType;
  final Map<String, dynamic> payload;

  /// True when the server sent this from its buffer to catch us up.
  final bool replay;
  final DateTime receivedAt;

  factory CallStreamEvent.fromJson(Map<String, dynamic> j) {
    final Map<String, dynamic> payload = <String, dynamic>{};
    final Object? raw = j['payload'];
    if (raw is Map<dynamic, dynamic>) {
      payload.addAll(raw.cast<String, dynamic>());
    }
    return CallStreamEvent(
      eventType: (j['event_type'] ?? 'event').toString(),
      payload: payload,
      replay: j['replay'] == true,
      receivedAt: DateTime.now(),
    );
  }
}

/// Connection state of the live stream, surfaced so the UI can show an honest
/// indicator rather than silently appearing empty.
enum CallStreamStatus { connecting, live, reconnecting, closed, failed }

class CallStreamUpdate {
  const CallStreamUpdate({required this.status, this.event, this.error});

  final CallStreamStatus status;
  final CallStreamEvent? event;
  final String? error;
}

/// Subscribes to `WS /ws/calls/{callId}` and reconnects with backoff.
///
/// The browser cannot set headers on a WebSocket handshake, so the bearer token
/// travels as a query parameter and is validated server-side.
class CallStreamClient {
  CallStreamClient({required this.callId, required this.token, this.baseUrl});

  final String callId;
  final String token;
  final String? baseUrl;

  final StreamController<CallStreamUpdate> _controller =
      StreamController<CallStreamUpdate>.broadcast();
  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _sub;
  Timer? _retryTimer;
  int _attempt = 0;
  bool _closedByUser = false;

  Stream<CallStreamUpdate> get updates => _controller.stream;

  void connect() {
    _closedByUser = false;
    _open();
  }

  void _open() {
    final String base = baseUrl ?? wsBaseUrl();
    final Uri uri = Uri.parse('$base/ws/calls/$callId').replace(
      queryParameters: <String, String>{'token': token},
    );
    _emit(const CallStreamUpdate(status: CallStreamStatus.connecting));

    try {
      final WebSocketChannel channel = WebSocketChannel.connect(uri);
      _channel = channel;
      _sub = channel.stream.listen(
        _onMessage,
        onError: (Object error) => _fail(error.toString()),
        onDone: _onDone,
        cancelOnError: false,
      );
      _attempt = 0;
      _emit(const CallStreamUpdate(status: CallStreamStatus.live));
    } catch (e) {
      _fail(e.toString());
    }
  }

  void _onMessage(dynamic raw) {
    if (raw is! String) return;
    try {
      final Object? decoded = jsonDecode(raw);
      if (decoded is Map<dynamic, dynamic>) {
        _emit(
          CallStreamUpdate(
            status: CallStreamStatus.live,
            event: CallStreamEvent.fromJson(decoded.cast<String, dynamic>()),
          ),
        );
      }
    } catch (_) {
      // Ignore malformed frames rather than tearing down the stream.
    }
  }

  void _onDone() {
    if (_closedByUser) {
      _emit(const CallStreamUpdate(status: CallStreamStatus.closed));
      return;
    }
    _scheduleReconnect();
  }

  void _fail(String message) {
    _emit(CallStreamUpdate(status: CallStreamStatus.failed, error: message));
    _scheduleReconnect();
  }

  void _scheduleReconnect() {
    if (_closedByUser) return;
    _attempt += 1;
    if (_attempt > 6) {
      _emit(
        const CallStreamUpdate(
          status: CallStreamStatus.failed,
          error: 'Live updates stopped. Reopen the call to reconnect.',
        ),
      );
      return;
    }
    _emit(const CallStreamUpdate(status: CallStreamStatus.reconnecting));
    final int delayMs = <int>[500, 1000, 2000, 4000, 8000, 12000][_attempt - 1];
    _retryTimer?.cancel();
    _retryTimer = Timer(Duration(milliseconds: delayMs), _open);
  }

  void _emit(CallStreamUpdate update) {
    if (!_controller.isClosed) _controller.add(update);
  }

  Future<void> dispose() async {
    _closedByUser = true;
    _retryTimer?.cancel();
    await _sub?.cancel();
    await _channel?.sink.close();
    await _controller.close();
  }
}
