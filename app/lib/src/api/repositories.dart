import 'dart:typed_data';

import 'package:dio/dio.dart';

import 'api_client.dart';
import 'models.dart';

/// Domain-grouped API access. Each method maps to one backend endpoint and
/// returns typed models. Errors surface as [ApiError] from [ApiClient].

class AuthRepository {
  AuthRepository(this._c);
  final ApiClient _c;

  Future<AuthSession> login(String email, String password) async {
    final Map<String, dynamic> json = await _c.postJson(
      '/auth/login',
      body: <String, String>{'email': email, 'password': password},
    );
    return AuthSession.fromJson(json);
  }

  Future<AuthSession> register({
    required String email,
    required String fullName,
    required String password,
    required String organizationName,
  }) async {
    final Map<String, dynamic> json = await _c.postJson(
      '/auth/register',
      body: <String, String>{
        'email': email,
        'full_name': fullName,
        'password': password,
        'organization_name': organizationName,
      },
    );
    return AuthSession.fromJson(json);
  }

  Future<Map<String, dynamic>> me() => _c.getJson('/auth/me');
}

class AgentRepository {
  AgentRepository(this._c);
  final ApiClient _c;

  Future<List<Agent>> list() async => (await _c.getList('/agents'))
      .map((dynamic e) =>
          Agent.fromJson((e as Map<dynamic, dynamic>).cast<String, dynamic>()))
      .toList();

  Future<Agent> get(String id) async =>
      Agent.fromJson(await _c.getJson('/agents/$id'));

  Future<Map<String, dynamic>> detail(String id) => _c.getJson('/agents/$id');

  Future<Agent> create(Map<String, dynamic> body) async =>
      Agent.fromJson(await _c.postJson('/agents', body: body));

  Future<Agent> update(String id, Map<String, dynamic> body) async =>
      Agent.fromJson(await _c.patchJson('/agents/$id', body: body));

  Future<Agent> duplicate(String id) async =>
      Agent.fromJson(await _c.postJson('/agents/$id/duplicate'));

  Future<void> delete(String id) => _c.delete('/agents/$id');

  Future<Map<String, dynamic>> test(
          String id, String message, List<String> kbIds) =>
      _c.postJson(
        '/agents/$id/test',
        body: <String, dynamic>{
          'message': message,
          'knowledge_base_ids': kbIds,
        },
      );
}

class TelephonyRepository {
  TelephonyRepository(this._c);
  final ApiClient _c;

  Future<List<PhoneConnection>> listConnections() async =>
      (await _c.getList('/phone-connections'))
          .map((dynamic e) => PhoneConnection.fromJson(
              (e as Map<dynamic, dynamic>).cast<String, dynamic>()))
          .toList();

  Future<PhoneConnection> createConnection(Map<String, dynamic> body) async =>
      PhoneConnection.fromJson(
          await _c.postJson('/phone-connections', body: body));

  Future<PhoneConnection> updateConnection(
          String id, Map<String, dynamic> body) async =>
      PhoneConnection.fromJson(
          await _c.patchJson('/phone-connections/$id', body: body));

  Future<void> deleteConnection(String id) =>
      _c.delete('/phone-connections/$id');

  /// Real probe. Returns whether the line verified plus the human-readable reason.
  Future<({bool verified, String status, String message})> verifyConnection(
      String id) async {
    final Map<String, dynamic> json =
        await _c.postJson('/phone-connections/$id/verify');
    return (
      verified: json.boolOr('verified', false),
      status: json.str('status', fallback: 'unknown'),
      message: json.str('message', fallback: 'Verification completed.'),
    );
  }

  Future<List<Gateway>> listGateways() async => (await _c.getList('/gateways'))
      .map((dynamic e) => Gateway.fromJson(
          (e as Map<dynamic, dynamic>).cast<String, dynamic>()))
      .toList();

  Future<Gateway> registerGateway(
          String identifier, String sipEndpoint) async =>
      Gateway.fromJson(
        await _c.postJson(
          '/gateways',
          body: <String, String>{
            'identifier': identifier,
            'sip_endpoint': sipEndpoint,
          },
        ),
      );

  Future<({Gateway gateway, GatewayProbe probe})> verifyGateway(
      String id) async {
    final Map<String, dynamic> json = await _c.postJson('/gateways/$id/verify');
    return (
      gateway: Gateway.fromJson(json),
      probe: GatewayProbe.fromJson(json.mapOr('probe')),
    );
  }

  Future<List<GatewayLine>> lines(String gatewayId) async {
    final Map<String, dynamic> json =
        await _c.getJson('/gateways/$gatewayId/lines');
    return json.listOfMaps('lines').map(GatewayLine.fromJson).toList();
  }

  Future<void> deleteGateway(String id) => _c.delete('/gateways/$id');

  Future<CapabilityMatrix> capabilities() async =>
      CapabilityMatrix.fromJson(await _c.getJson('/telephony/capabilities'));

  Future<Map<String, dynamic>> health() => _c.getJson('/telephony/health');
}

class CallRepository {
  CallRepository(this._c);
  final ApiClient _c;

  Future<List<CallSummary>> list(
      {String? status, String? direction, int limit = 100}) async {
    final List<dynamic> raw = await _c.getList(
      '/calls',
      query: <String, dynamic>{
        'limit': limit,
        if (status != null) 'status': status,
        if (direction != null) 'direction': direction,
      },
    );
    return raw
        .map((dynamic e) => CallSummary.fromJson(
            (e as Map<dynamic, dynamic>).cast<String, dynamic>()))
        .toList();
  }

  Future<CallDetail> detail(String id) async =>
      CallDetail.fromJson(await _c.getJson('/calls/$id'));

  /// Downloads the audio the AI produced on this call (agent side only).
  Future<Uint8List> agentAudio(String id) async {
    final List<int> bytes = await _c.getBytes('/calls/$id/agent-audio');
    return Uint8List.fromList(bytes);
  }

  Future<Map<String, dynamic>> simulate(
          {String? agentId, String scenario = 'order_tracking'}) =>
      _c.postJson(
        '/calls/simulate',
        body: <String, dynamic>{
          if (agentId != null) 'agent_id': agentId,
          'scenario': scenario,
        },
      );

  Future<Map<String, dynamic>> placeOutbound({
    required String toNumber,
    String? connectionId,
    String? agentId,
    String? reason,
    bool confirmed = true,
  }) =>
      _c.postJson(
        '/calls/outbound',
        body: <String, dynamic>{
          'to_number': toNumber,
          'connection_id': connectionId,
          'agent_id': agentId,
          'reason': reason,
          'confirmed': confirmed,
        },
      );
}

class KnowledgeRepository {
  KnowledgeRepository(this._c);
  final ApiClient _c;

  Future<List<KnowledgeBase>> listBases() async =>
      (await _c.getList('/knowledge-bases'))
          .map((dynamic e) => KnowledgeBase.fromJson(
              (e as Map<dynamic, dynamic>).cast<String, dynamic>()))
          .toList();

  Future<KnowledgeBase> createBase(String name, String? description) async =>
      KnowledgeBase.fromJson(
        await _c.postJson(
          '/knowledge-bases',
          body: <String, dynamic>{
            'name': name,
            if (description != null && description.isNotEmpty)
              'description': description,
          },
        ),
      );

  Future<void> deleteBase(String id) => _c.delete('/knowledge-bases/$id');

  Future<List<KnowledgeDocument>> listDocuments(String kbId) async =>
      (await _c.getList('/knowledge-bases/$kbId/documents'))
          .map((dynamic e) => KnowledgeDocument.fromJson(
              (e as Map<dynamic, dynamic>).cast<String, dynamic>()))
          .toList();

  Future<void> deleteDocument(String documentId) =>
      _c.delete('/knowledge-bases/documents/$documentId');

  Future<KnowledgeDocument> upload(
      String kbId, String filename, List<int> bytes) async {
    final FormData form = FormData.fromMap(<String, dynamic>{
      'file': MultipartFile.fromBytes(bytes, filename: filename),
    });
    final Map<String, dynamic> json = await _c
        .postJson('/knowledge-bases/$kbId/documents/upload', body: form);
    return KnowledgeDocument.fromJson(json);
  }

  Future<List<Map<String, dynamic>>> search(String query,
      {String? kbId, int topK = 4}) async {
    final List<dynamic> raw = await _c.postList(
      '/knowledge-bases/search',
      body: <String, dynamic>{
        'query': query,
        if (kbId != null) 'knowledge_base_id': kbId,
        'top_k': topK,
      },
    );
    return raw
        .map(
            (dynamic e) => (e as Map<dynamic, dynamic>).cast<String, dynamic>())
        .toList();
  }
}

class CampaignRepository {
  CampaignRepository(this._c);
  final ApiClient _c;

  Future<List<Campaign>> list() async => (await _c.getList('/campaigns'))
      .map((dynamic e) => Campaign.fromJson(
          (e as Map<dynamic, dynamic>).cast<String, dynamic>()))
      .toList();

  Future<Campaign> create(Map<String, dynamic> body) async =>
      Campaign.fromJson(await _c.postJson('/campaigns', body: body));

  Future<Map<String, dynamic>> dryRun(String id) =>
      _c.postJson('/campaigns/$id/dry-run');

  Future<Map<String, dynamic>> start(String id) =>
      _c.postJson('/campaigns/$id/start');

  /// Runs one more dialer pass over the campaign's pending contacts.
  Future<Map<String, dynamic>> sweep(String id) =>
      _c.postJson('/campaigns/$id/sweep');

  Future<Map<String, dynamic>> pause(String id) =>
      _c.postJson('/campaigns/$id/pause');
}

class ContactRepository {
  ContactRepository(this._c);
  final ApiClient _c;

  Future<List<Contact>> list(
      {String? search, bool? suppressed, int limit = 100}) async {
    final List<dynamic> raw = await _c.getList(
      '/contacts',
      query: <String, dynamic>{
        'limit': limit,
        if (search != null && search.isNotEmpty) 'search': search,
        if (suppressed != null) 'is_suppressed': suppressed,
      },
    );
    return raw
        .map((dynamic e) => Contact.fromJson(
            (e as Map<dynamic, dynamic>).cast<String, dynamic>()))
        .toList();
  }

  Future<Contact> create(Map<String, dynamic> body) async =>
      Contact.fromJson(await _c.postJson('/contacts', body: body));

  Future<Map<String, dynamic>> suppress(String phoneNumber,
          {String reason = 'caller_requested_opt_out'}) =>
      _c.postJson(
        '/contacts/suppress',
        body: <String, String>{
          'phone_number': phoneNumber,
          'reason': reason,
        },
      );
}

class AnalyticsRepository {
  AnalyticsRepository(this._c);
  final ApiClient _c;

  Future<AnalyticsOverview> summary({int days = 30}) async =>
      AnalyticsOverview.fromJson(await _c.getJson('/analytics/summary',
          query: <String, dynamic>{'days': days}));
}

class AuditRepository {
  AuditRepository(this._c);
  final ApiClient _c;

  Future<List<AuditEntry>> list({int limit = 100}) async => (await _c
          .getList('/audit-logs', query: <String, dynamic>{'limit': limit}))
      .map((dynamic e) => AuditEntry.fromJson(
          (e as Map<dynamic, dynamic>).cast<String, dynamic>()))
      .toList();
}

class TeamRepository {
  TeamRepository(this._c);
  final ApiClient _c;

  Future<Map<String, dynamic>> currentOrganization() =>
      _c.getJson('/organizations/current');

  Future<List<Map<String, dynamic>>> members() async {
    final List<dynamic> raw = await _c.getList('/organizations/members');
    return raw
        .map(
            (dynamic e) => (e as Map<dynamic, dynamic>).cast<String, dynamic>())
        .toList();
  }

  Future<Map<String, dynamic>> invite(String email, String role) =>
      _c.postJson('/organizations/invite',
          body: <String, String>{'email': email, 'role': role});

  Future<List<Map<String, dynamic>>> invitations() async {
    final List<dynamic> raw = await _c.getList('/organizations/invitations');
    return raw
        .map(
            (dynamic e) => (e as Map<dynamic, dynamic>).cast<String, dynamic>())
        .toList();
  }

  /// Owner-only server-side.
  Future<void> updateRole(String membershipId, String role) =>
      _c.patchJson('/organizations/members/$membershipId',
          body: <String, String>{'role': role});

  Future<void> remove(String membershipId) =>
      _c.delete('/organizations/members/$membershipId');
}

class HealthRepository {
  HealthRepository(this._c);
  final ApiClient _c;

  Future<Map<String, dynamic>> ready() => _c.getJson('/health/ready');
}
