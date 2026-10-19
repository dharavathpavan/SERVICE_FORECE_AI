import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../api/models.dart';
import '../api/repositories.dart';
import 'session_store.dart';

/// UI theme preference. Defaults to light; settings can flip it.
final StateProvider<ThemeMode> themeModeProvider =
    StateProvider<ThemeMode>((Ref ref) => ThemeMode.light);

// --------------------------------------------------------------------------- //
// Infrastructure
// --------------------------------------------------------------------------- //

final Provider<SessionStore> sessionStoreProvider =
    Provider<SessionStore>((Ref ref) {
  return SessionStore();
});

final Provider<ApiClient> apiClientProvider = Provider<ApiClient>((Ref ref) {
  final SessionStore store = ref.watch(sessionStoreProvider);
  return ApiClient(tokens: store);
});

final Provider<AuthRepository> authRepositoryProvider =
    Provider<AuthRepository>(
        (Ref ref) => AuthRepository(ref.watch(apiClientProvider)));
final Provider<AgentRepository> agentRepositoryProvider =
    Provider<AgentRepository>(
        (Ref ref) => AgentRepository(ref.watch(apiClientProvider)));
final Provider<TelephonyRepository> telephonyRepositoryProvider =
    Provider<TelephonyRepository>(
        (Ref ref) => TelephonyRepository(ref.watch(apiClientProvider)));
final Provider<CallRepository> callRepositoryProvider =
    Provider<CallRepository>(
        (Ref ref) => CallRepository(ref.watch(apiClientProvider)));
final Provider<KnowledgeRepository> knowledgeRepositoryProvider =
    Provider<KnowledgeRepository>(
        (Ref ref) => KnowledgeRepository(ref.watch(apiClientProvider)));
final Provider<CampaignRepository> campaignRepositoryProvider =
    Provider<CampaignRepository>(
        (Ref ref) => CampaignRepository(ref.watch(apiClientProvider)));
final Provider<ContactRepository> contactRepositoryProvider =
    Provider<ContactRepository>(
        (Ref ref) => ContactRepository(ref.watch(apiClientProvider)));
final Provider<AnalyticsRepository> analyticsRepositoryProvider =
    Provider<AnalyticsRepository>(
        (Ref ref) => AnalyticsRepository(ref.watch(apiClientProvider)));
final Provider<AuditRepository> auditRepositoryProvider =
    Provider<AuditRepository>(
        (Ref ref) => AuditRepository(ref.watch(apiClientProvider)));
final Provider<TeamRepository> teamRepositoryProvider =
    Provider<TeamRepository>(
        (Ref ref) => TeamRepository(ref.watch(apiClientProvider)));
final Provider<HealthRepository> healthRepositoryProvider =
    Provider<HealthRepository>(
        (Ref ref) => HealthRepository(ref.watch(apiClientProvider)));

// --------------------------------------------------------------------------- //
// Auth
// --------------------------------------------------------------------------- //

/// Current session state, kept in sync with [SessionStore].
final NotifierProvider<AuthController, AuthState> authProvider =
    NotifierProvider<AuthController, AuthState>(AuthController.new);

class AuthState {
  const AuthState(
      {this.session, this.busy = false, this.error, this.ready = false});

  final AuthSession? session;
  final bool busy;
  final Object? error;
  final bool ready;

  bool get isAuthenticated => session != null;

  AuthState copyWith({
    AuthSession? session,
    bool? busy,
    Object? error,
    bool? ready,
    bool clearError = false,
  }) {
    return AuthState(
      session: session ?? this.session,
      busy: busy ?? this.busy,
      error: clearError ? null : (error ?? this.error),
      ready: ready ?? this.ready,
    );
  }
}

class AuthController extends Notifier<AuthState> {
  late final SessionStore _store;

  @override
  AuthState build() {
    _store = ref.watch(sessionStoreProvider);
    _store.addListener(_sync);
    ref.onDispose(() => _store.removeListener(_sync));
    return AuthState(session: _store.session, ready: _store.ready);
  }

  void _sync() {
    state = state.copyWith(session: _store.session, ready: _store.ready);
  }

  Future<void> restore() async {
    await _store.restore();
    state = state.copyWith(session: _store.session, ready: true);
  }

  Future<bool> login(String email, String password) async {
    state = state.copyWith(busy: true, clearError: true);
    try {
      final AuthSession session =
          await ref.read(authRepositoryProvider).login(email.trim(), password);
      await _store.save(session);
      state = AuthState(session: session, busy: false, ready: true);
      return true;
    } catch (e) {
      state = state.copyWith(busy: false, error: e);
      return false;
    }
  }

  Future<bool> register({
    required String email,
    required String fullName,
    required String password,
    required String organizationName,
  }) async {
    state = state.copyWith(busy: true, clearError: true);
    try {
      final AuthSession session =
          await ref.read(authRepositoryProvider).register(
                email: email.trim(),
                fullName: fullName.trim(),
                password: password,
                organizationName: organizationName.trim(),
              );
      await _store.save(session);
      state = AuthState(session: session, busy: false, ready: true);
      return true;
    } catch (e) {
      state = state.copyWith(busy: false, error: e);
      return false;
    }
  }

  Future<void> logout() async {
    await _store.clear();
    state = const AuthState(ready: true);
  }
}

// --------------------------------------------------------------------------- //
// Data
// --------------------------------------------------------------------------- //

final FutureProvider<List<Agent>> agentsProvider =
    FutureProvider<List<Agent>>((Ref ref) {
  return ref.watch(agentRepositoryProvider).list();
});

final FutureProviderFamily<Map<String, dynamic>, String> agentDetailProvider =
    FutureProvider.family<Map<String, dynamic>, String>((Ref ref, String id) {
  return ref.watch(agentRepositoryProvider).detail(id);
});

final FutureProvider<List<PhoneConnection>> phoneConnectionsProvider =
    FutureProvider<List<PhoneConnection>>((Ref ref) {
  return ref.watch(telephonyRepositoryProvider).listConnections();
});

final FutureProvider<List<Gateway>> gatewaysProvider =
    FutureProvider<List<Gateway>>((Ref ref) {
  return ref.watch(telephonyRepositoryProvider).listGateways();
});

final FutureProvider<CapabilityMatrix> telephonyCapabilitiesProvider =
    FutureProvider<CapabilityMatrix>((Ref ref) {
  return ref.watch(telephonyRepositoryProvider).capabilities();
});

final FutureProvider<List<CallSummary>> callsProvider =
    FutureProvider<List<CallSummary>>((Ref ref) {
  return ref.watch(callRepositoryProvider).list();
});

final FutureProviderFamily<CallDetail, String> callDetailProvider =
    FutureProvider.family<CallDetail, String>((Ref ref, String id) {
  return ref.watch(callRepositoryProvider).detail(id);
});

final FutureProvider<List<KnowledgeBase>> knowledgeBasesProvider =
    FutureProvider<List<KnowledgeBase>>((Ref ref) {
  return ref.watch(knowledgeRepositoryProvider).listBases();
});

final FutureProviderFamily<List<KnowledgeDocument>, String> documentsProvider =
    FutureProvider.family<List<KnowledgeDocument>, String>(
        (Ref ref, String kbId) {
  return ref.watch(knowledgeRepositoryProvider).listDocuments(kbId);
});

final FutureProvider<List<Campaign>> campaignsProvider =
    FutureProvider<List<Campaign>>((Ref ref) {
  return ref.watch(campaignRepositoryProvider).list();
});

final FutureProvider<List<Contact>> contactsProvider =
    FutureProvider<List<Contact>>((Ref ref) {
  return ref.watch(contactRepositoryProvider).list();
});

final FutureProvider<AnalyticsOverview> analyticsProvider =
    FutureProvider<AnalyticsOverview>((Ref ref) {
  return ref.watch(analyticsRepositoryProvider).summary();
});

final FutureProvider<List<AuditEntry>> auditLogsProvider =
    FutureProvider<List<AuditEntry>>((Ref ref) {
  return ref.watch(auditRepositoryProvider).list();
});

final FutureProvider<List<Map<String, dynamic>>> teamMembersProvider =
    FutureProvider<List<Map<String, dynamic>>>((Ref ref) {
  return ref.watch(teamRepositoryProvider).members();
});

final FutureProvider<Map<String, dynamic>> healthReadyProvider =
    FutureProvider<Map<String, dynamic>>((Ref ref) {
  return ref.watch(healthRepositoryProvider).ready();
});
