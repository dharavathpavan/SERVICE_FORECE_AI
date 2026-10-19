import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../api/api_client.dart';
import '../api/models.dart';

/// Holds the authenticated session and exposes the values [ApiClient] needs.
///
/// Kept deliberately small and free of Riverpod so the API client can depend on
/// it without a circular provider graph.
class SessionStore extends ChangeNotifier implements TokenProvider {
  SessionStore({FlutterSecureStorage? storage, this.onSignedOut})
      : _storage = storage ?? const FlutterSecureStorage();

  static const String _kToken = 'sf.access_token';
  static const String _kOrgId = 'sf.organization_id';
  static const String _kOrgName = 'sf.organization_name';
  static const String _kRole = 'sf.role';
  static const String _kUserJson = 'sf.user';

  final FlutterSecureStorage _storage;
  final FutureOr<void> Function()? onSignedOut;

  AuthSession? _session;
  bool _ready = false;

  AuthSession? get session => _session;
  bool get isAuthenticated => _session != null;
  bool get ready => _ready;
  AppUser? get user => _session?.user;

  @override
  String? get accessToken => _session?.token;

  @override
  String? get organizationId => _session?.organizationId;

  /// Restores a persisted session on startup.
  Future<void> restore() async {
    try {
      final String? token = await _storage.read(key: _kToken);
      final String? orgId = await _storage.read(key: _kOrgId);
      final String? orgName = await _storage.read(key: _kOrgName);
      final String? role = await _storage.read(key: _kRole);
      final String? userJson = await _storage.read(key: _kUserJson);
      if (token != null && orgId != null && userJson != null) {
        _session = AuthSession(
          token: token,
          user: _userFromCsv(userJson),
          organizationId: orgId,
          organizationName: orgName ?? 'Workspace',
          role: role ?? 'operator',
        );
      }
    } catch (_) {
      // Corrupt or unavailable storage: start signed out rather than crash.
      _session = null;
    } finally {
      _ready = true;
      notifyListeners();
    }
  }

  Future<void> save(AuthSession session) async {
    _session = session;
    notifyListeners();
    await _storage.write(key: _kToken, value: session.token);
    await _storage.write(key: _kOrgId, value: session.organizationId);
    await _storage.write(key: _kOrgName, value: session.organizationName);
    await _storage.write(key: _kRole, value: session.role);
    await _storage.write(
      key: _kUserJson,
      value:
          '${session.user.id}|${session.user.email}|${session.user.fullName}|${session.user.isActive}',
    );
  }

  Future<void> clear() async {
    _session = null;
    notifyListeners();
    await _storage.delete(key: _kToken);
    await _storage.delete(key: _kOrgId);
    await _storage.delete(key: _kOrgName);
    await _storage.delete(key: _kRole);
    await _storage.delete(key: _kUserJson);
  }

  @override
  Future<void> onUnauthorized() async {
    if (_session == null) return;
    await clear();
    await onSignedOut?.call();
  }

  static AppUser _userFromCsv(String csv) {
    final List<String> parts = csv.split('|');
    return AppUser(
      id: parts.isNotEmpty ? parts[0] : '',
      email: parts.length > 1 ? parts[1] : '',
      fullName: parts.length > 2 ? parts[2] : 'User',
      isActive: parts.length > 3 ? parts[3] == 'true' : true,
    );
  }
}
