import 'api_client.dart';

/// Immutable view models mirroring the API. All parsing is defensive: a missing
/// or mistyped field falls back to a safe default rather than throwing.

class AppUser {
  const AppUser(
      {required this.id,
      required this.email,
      required this.fullName,
      required this.isActive});

  final String id;
  final String email;
  final String fullName;
  final bool isActive;

  factory AppUser.fromJson(Map<String, dynamic> j) => AppUser(
        id: j.str('id'),
        email: j.str('email'),
        fullName: j.str('full_name', fallback: 'Unknown user'),
        isActive: j.boolOr('is_active', true),
      );
}

class AuthSession {
  const AuthSession({
    required this.token,
    required this.user,
    required this.organizationId,
    required this.organizationName,
    required this.role,
  });

  final String token;
  final AppUser user;
  final String organizationId;
  final String organizationName;
  final String role;

  factory AuthSession.fromJson(Map<String, dynamic> j) => AuthSession(
        token: j.str('access_token'),
        user: AppUser.fromJson(j.mapOr('user')),
        organizationId: j.str('organization_id'),
        organizationName: j.str('organization_name', fallback: 'Workspace'),
        role: j.str('role', fallback: 'operator'),
      );
}

enum AgentDirection {
  inbound,
  outbound,
  both;

  static AgentDirection parse(String v) =>
      AgentDirection.values.firstWhere((AgentDirection e) => e.name == v,
          orElse: () => AgentDirection.both);

  String get label => switch (this) {
        AgentDirection.inbound => 'Inbound',
        AgentDirection.outbound => 'Outbound',
        AgentDirection.both => 'Inbound & outbound',
      };
}

class Agent {
  const Agent({
    required this.id,
    required this.name,
    required this.purpose,
    required this.language,
    required this.voice,
    required this.greeting,
    required this.systemPrompt,
    required this.direction,
    required this.isActive,
    required this.maxDurationSeconds,
    this.humanTransferNumber,
    this.description,
    this.fallbackBehavior = '',
    this.activeVersionNumber = 1,
    this.createdAt,
  });

  final String id;
  final String name;
  final String purpose;
  final String language;
  final String voice;
  final String greeting;
  final String systemPrompt;
  final AgentDirection direction;
  final bool isActive;
  final int maxDurationSeconds;
  final String? humanTransferNumber;
  final String? description;
  final String fallbackBehavior;
  final int activeVersionNumber;
  final DateTime? createdAt;

  factory Agent.fromJson(Map<String, dynamic> j) => Agent(
        id: j.str('id'),
        name: j.str('name', fallback: 'Untitled agent'),
        purpose: j.str('purpose', fallback: 'Customer support'),
        language: j.str('language', fallback: 'en-US'),
        voice: j.str('voice', fallback: 'Puck'),
        greeting: j.str('greeting'),
        systemPrompt: j.str('system_prompt'),
        direction: AgentDirection.parse(j.str('direction', fallback: 'both')),
        isActive: j.boolOr('is_active', true),
        maxDurationSeconds: j.intOr('max_duration_seconds', 600),
        humanTransferNumber: j.optString('human_transfer_number'),
        description: j.optString('description'),
        fallbackBehavior: j.str('fallback_behavior'),
        activeVersionNumber: j.intOr('active_version_number', 1),
        createdAt: j.dateOrNull('created_at'),
      );
}

class PhoneConnection {
  const PhoneConnection({
    required this.id,
    required this.friendlyName,
    required this.phoneNumber,
    required this.connectionType,
    required this.isVerified,
    required this.healthStatus,
    required this.inboundEnabled,
    required this.outboundEnabled,
    this.assignedAgentId,
    this.lastHealthCheck,
  });

  final String id;
  final String friendlyName;
  final String phoneNumber;
  final String connectionType;
  final bool isVerified;
  final String healthStatus;
  final bool inboundEnabled;
  final bool outboundEnabled;
  final String? assignedAgentId;
  final DateTime? lastHealthCheck;

  factory PhoneConnection.fromJson(Map<String, dynamic> j) => PhoneConnection(
        id: j.str('id'),
        friendlyName: j.str('friendly_name', fallback: 'Unnamed line'),
        phoneNumber: j.str('phone_number'),
        connectionType: j.str('connection_type', fallback: 'mock'),
        isVerified: j.boolOr('is_verified', false),
        healthStatus: j.str('health_status', fallback: 'unverified'),
        inboundEnabled: j.boolOr('inbound_enabled', true),
        outboundEnabled: j.boolOr('outbound_enabled', true),
        assignedAgentId: j.optString('assigned_agent_id'),
        lastHealthCheck: j.dateOrNull('last_health_check'),
      );
}

/// Gateway status is never assumed: `unverified` means no probe has succeeded yet.
enum GatewayStatus {
  unverified,
  online,
  degraded,
  offline;

  static GatewayStatus parse(String v) =>
      GatewayStatus.values.firstWhere((GatewayStatus e) => e.name == v,
          orElse: () => GatewayStatus.unverified);

  String get label => switch (this) {
        GatewayStatus.unverified => 'Not verified',
        GatewayStatus.online => 'Online',
        GatewayStatus.degraded => 'Degraded',
        GatewayStatus.offline => 'Offline',
      };
}

class GatewayLine {
  const GatewayLine({
    required this.lineId,
    required this.state,
    required this.usable,
    required this.registrationOk,
    required this.simPresent,
    this.phoneNumber,
    this.carrier,
    this.signalPercent,
    this.activeChannels = 0,
    this.detail,
  });

  final String lineId;
  final String state;
  final bool usable;
  final bool registrationOk;
  final bool simPresent;
  final String? phoneNumber;
  final String? carrier;
  final int? signalPercent;
  final int activeChannels;
  final String? detail;

  factory GatewayLine.fromJson(Map<String, dynamic> j) => GatewayLine(
        lineId: j.str('line_id', fallback: 'line'),
        state: j.str('state', fallback: 'unknown'),
        usable: j.boolOr('usable', false),
        registrationOk: j.boolOr('registration_ok', false),
        simPresent: j.boolOr('sim_present', true),
        phoneNumber: j.optString('phone_number'),
        carrier: j.optString('carrier'),
        signalPercent: j['signal_percent'] is num
            ? (j['signal_percent'] as num).toInt()
            : null,
        activeChannels: j.intOr('active_channels', 0),
        detail: j.optString('detail'),
      );
}

class Gateway {
  const Gateway({
    required this.id,
    required this.identifier,
    required this.sipEndpoint,
    required this.status,
    required this.connected,
    required this.needsVerification,
    required this.healthDetails,
    this.lastHeartbeat,
  });

  final String id;
  final String identifier;
  final String sipEndpoint;
  final GatewayStatus status;
  final bool connected;
  final bool needsVerification;
  final Map<String, dynamic> healthDetails;
  final DateTime? lastHeartbeat;

  factory Gateway.fromJson(Map<String, dynamic> j) => Gateway(
        id: j.str('id'),
        identifier: j.str('identifier', fallback: 'gateway'),
        sipEndpoint: j.str('sip_endpoint'),
        status: GatewayStatus.parse(j.str('status', fallback: 'unverified')),
        connected: j.boolOr('connected', false),
        needsVerification: j.boolOr('needs_verification', true),
        healthDetails: j.mapOr('health_details'),
        lastHeartbeat: j.dateOrNull('last_heartbeat'),
      );
}

class GatewayProbe {
  const GatewayProbe({
    required this.ok,
    required this.status,
    required this.message,
    required this.lines,
    this.latencyMs,
    this.errors = const <String>[],
  });

  final bool ok;
  final String status;
  final String message;
  final List<GatewayLine> lines;
  final double? latencyMs;
  final List<String> errors;

  factory GatewayProbe.fromJson(Map<String, dynamic> j) => GatewayProbe(
        ok: j.boolOr('ok', false),
        status: j.str('status', fallback: 'unknown'),
        message: j.str('message', fallback: 'No message returned.'),
        lines: j.listOfMaps('lines').map(GatewayLine.fromJson).toList(),
        latencyMs:
            j['latency_ms'] is num ? (j['latency_ms'] as num).toDouble() : null,
        errors: (j['errors'] as List<dynamic>? ?? const <dynamic>[])
            .whereType<String>()
            .toList(),
      );
}

class CapabilityMatrix {
  const CapabilityMatrix(
      {required this.provider,
      required this.capabilities,
      required this.notes});

  final String provider;
  final Map<String, String> capabilities;
  final List<String> notes;

  factory CapabilityMatrix.fromJson(Map<String, dynamic> j) => CapabilityMatrix(
        provider: j.str('provider', fallback: 'unknown'),
        capabilities: j
            .mapOr('capabilities')
            .map((String k, dynamic v) => MapEntry<String, String>(k, '$v')),
        notes: (j['notes'] as List<dynamic>? ?? const <dynamic>[])
            .whereType<String>()
            .toList(),
      );
}

class CallSummary {
  const CallSummary({
    required this.id,
    required this.phoneNumber,
    required this.direction,
    required this.status,
    required this.outcome,
    required this.durationSeconds,
    required this.estimatedCost,
    this.agentId,
    this.callerId,
    this.summary,
    this.startTime,
    this.createdAt,
  });

  final String id;
  final String phoneNumber;
  final String direction;
  final String status;
  final String outcome;
  final int durationSeconds;
  final double estimatedCost;
  final String? agentId;
  final String? callerId;
  final String? summary;
  final DateTime? startTime;
  final DateTime? createdAt;

  factory CallSummary.fromJson(Map<String, dynamic> j) => CallSummary(
        id: j.str('id'),
        phoneNumber: j.str('phone_number'),
        direction: j.str('direction', fallback: 'inbound'),
        status: j.str('status', fallback: 'queued'),
        outcome: j.str('outcome'),
        durationSeconds: j.intOr('duration_seconds', 0),
        estimatedCost: j.doubleOr('estimated_cost', 0),
        agentId: j.optString('agent_id'),
        callerId: j.optString('caller_id'),
        summary: j.optString('summary'),
        startTime: j.dateOrNull('start_time'),
        createdAt: j.dateOrNull('created_at'),
      );
}

class CallEventItem {
  const CallEventItem(
      {required this.eventType, required this.payload, this.createdAt});

  final String eventType;
  final Map<String, dynamic> payload;
  final DateTime? createdAt;

  factory CallEventItem.fromJson(Map<String, dynamic> j) => CallEventItem(
        eventType: j.str('event_type', fallback: 'event'),
        payload: j.mapOr('payload'),
        createdAt: j.dateOrNull('created_at'),
      );
}

class TranscriptTurn {
  const TranscriptTurn({
    required this.speaker,
    required this.text,
    required this.startMs,
    required this.endMs,
  });

  final String speaker;
  final String text;
  final int startMs;
  final int endMs;

  factory TranscriptTurn.fromJson(Map<String, dynamic> j) => TranscriptTurn(
        speaker: j.str('speaker', fallback: 'agent'),
        text: j.str('text'),
        startMs: j.intOr('start_timestamp_ms', 0),
        endMs: j.intOr('end_timestamp_ms', 0),
      );
}

class CallDetail {
  const CallDetail({
    required this.call,
    required this.events,
    required this.transcripts,
    this.recordingUrl,
    this.agentAudioUrl,
  });

  final CallSummary call;
  final List<CallEventItem> events;
  final List<TranscriptTurn> transcripts;

  /// Carrier/gateway recording, when the telephony provider supplies one.
  final String? recordingUrl;

  /// Endpoint that streams the audio the AI generated (agent side only).
  final String? agentAudioUrl;

  factory CallDetail.fromJson(Map<String, dynamic> j) => CallDetail(
        call: CallSummary.fromJson(j),
        events: j.listOfMaps('events').map(CallEventItem.fromJson).toList(),
        transcripts:
            j.listOfMaps('transcripts').map(TranscriptTurn.fromJson).toList(),
        recordingUrl: j.optString('recording_url'),
        agentAudioUrl: j.optString('agent_audio_url'),
      );

  /// Engine that produced the stored agent audio, if the call recorded one.
  String? get agentAudioEngine {
    for (final CallEventItem event in events) {
      if (event.eventType == 'agent_audio_stored') {
        final Object? engine = event.payload['engine'];
        if (engine is String && engine.isNotEmpty) return engine;
      }
    }
    return null;
  }
}

class KnowledgeBase {
  const KnowledgeBase(
      {required this.id, required this.name, this.description, this.createdAt});

  final String id;
  final String name;
  final String? description;
  final DateTime? createdAt;

  factory KnowledgeBase.fromJson(Map<String, dynamic> j) => KnowledgeBase(
        id: j.str('id'),
        name: j.str('name', fallback: 'Untitled base'),
        description: j.optString('description'),
        createdAt: j.dateOrNull('created_at'),
      );
}

class KnowledgeDocument {
  const KnowledgeDocument({
    required this.id,
    required this.title,
    required this.fileType,
    required this.status,
    required this.chunkCount,
    this.errorMessage,
    this.fileSize = 0,
    this.createdAt,
  });

  final String id;
  final String title;
  final String fileType;
  final String status;
  final int chunkCount;
  final String? errorMessage;
  final int fileSize;
  final DateTime? createdAt;

  factory KnowledgeDocument.fromJson(Map<String, dynamic> j) =>
      KnowledgeDocument(
        id: j.str('id'),
        title: j.str('title', fallback: 'Untitled document'),
        fileType: j.str('file_type', fallback: 'txt'),
        status: j.str('status', fallback: 'queued'),
        chunkCount: j.intOr('chunk_count', 0),
        errorMessage: j.optString('error_message'),
        fileSize: j.intOr('file_size', 0),
        createdAt: j.dateOrNull('created_at'),
      );
}

class Campaign {
  const Campaign({
    required this.id,
    required this.name,
    required this.status,
    required this.totalContacts,
    required this.successfulCalls,
    required this.failedCalls,
    required this.allowedStartHour,
    required this.allowedEndHour,
    required this.maxAttempts,
    required this.concurrencyLimit,
    this.agentId,
  });

  final String id;
  final String name;
  final String status;
  final int totalContacts;
  final int successfulCalls;
  final int failedCalls;
  final String allowedStartHour;
  final String allowedEndHour;
  final int maxAttempts;
  final int concurrencyLimit;
  final String? agentId;

  factory Campaign.fromJson(Map<String, dynamic> j) => Campaign(
        id: j.str('id'),
        name: j.str('name', fallback: 'Untitled campaign'),
        status: j.str('status', fallback: 'draft'),
        totalContacts: j.intOr('total_contacts', 0),
        successfulCalls: j.intOr('successful_calls', 0),
        failedCalls: j.intOr('failed_calls', 0),
        allowedStartHour: j.str('allowed_start_hour', fallback: '09:00'),
        allowedEndHour: j.str('allowed_end_hour', fallback: '20:00'),
        maxAttempts: j.intOr('max_attempts', 3),
        concurrencyLimit: j.intOr('concurrency_limit', 2),
        agentId: j.optString('agent_id'),
      );
}

class Contact {
  const Contact({
    required this.id,
    required this.phoneNumber,
    required this.isSuppressed,
    this.firstName,
    this.lastName,
    this.email,
  });

  final String id;
  final String phoneNumber;
  final bool isSuppressed;
  final String? firstName;
  final String? lastName;
  final String? email;

  String get displayName {
    final String name =
        <String?>[firstName, lastName].whereType<String>().join(' ').trim();
    return name.isEmpty ? phoneNumber : name;
  }

  factory Contact.fromJson(Map<String, dynamic> j) => Contact(
        id: j.str('id'),
        phoneNumber: j.str('phone_number'),
        isSuppressed: j.boolOr('is_suppressed', false),
        firstName: j.optString('first_name'),
        lastName: j.optString('last_name'),
        email: j.optString('email'),
      );
}

class AuditEntry {
  const AuditEntry({
    required this.action,
    required this.entityType,
    this.entityId,
    this.createdAt,
    this.details = const <String, dynamic>{},
  });

  final String action;
  final String entityType;
  final String? entityId;
  final DateTime? createdAt;
  final Map<String, dynamic> details;

  factory AuditEntry.fromJson(Map<String, dynamic> j) => AuditEntry(
        action: j.str('action', fallback: 'action'),
        entityType: j.str('entity_type', fallback: 'entity'),
        entityId: j.optString('entity_id'),
        createdAt: j.dateOrNull('created_at'),
        details: j.mapOr('details'),
      );
}

class DailyVolumePoint {
  const DailyVolumePoint({
    required this.label,
    required this.totalCalls,
    required this.aiResolved,
    required this.transferred,
  });

  final String label;
  final int totalCalls;
  final int aiResolved;
  final int transferred;

  factory DailyVolumePoint.fromJson(Map<String, dynamic> j) => DailyVolumePoint(
        label: j.str('label', fallback: j.str('date')),
        totalCalls: j.intOr('total_calls', 0),
        aiResolved: j.intOr('ai_resolved', 0),
        transferred: j.intOr('transferred', 0),
      );
}

class AnalyticsOverview {
  const AnalyticsOverview({
    required this.callsToday,
    required this.totalCalls,
    required this.answeredCalls,
    required this.failedCalls,
    required this.aiResolved,
    required this.humanTransfers,
    required this.totalMinutes,
    required this.avgDurationSeconds,
    required this.estimatedCostUsd,
    required this.activeAgents,
    required this.runningCampaigns,
    required this.answerRatePct,
    required this.aiResolutionRatePct,
    required this.humanTransferRatePct,
    required this.dailyVolume,
  });

  final int callsToday;
  final int totalCalls;
  final int answeredCalls;
  final int failedCalls;
  final int aiResolved;
  final int humanTransfers;
  final double totalMinutes;
  final double avgDurationSeconds;
  final double estimatedCostUsd;
  final int activeAgents;
  final int runningCampaigns;
  final double answerRatePct;
  final double aiResolutionRatePct;
  final double humanTransferRatePct;
  final List<DailyVolumePoint> dailyVolume;

  factory AnalyticsOverview.fromJson(Map<String, dynamic> j) =>
      AnalyticsOverview(
        callsToday: j.intOr('calls_today', 0),
        totalCalls: j.intOr('total_calls', 0),
        answeredCalls: j.intOr('answered_calls', 0),
        failedCalls: j.intOr('failed_calls', 0),
        aiResolved: j.intOr('ai_resolved_calls', 0),
        humanTransfers: j.intOr('human_transfers', 0),
        totalMinutes: j.doubleOr('total_minutes', 0),
        avgDurationSeconds: j.doubleOr('avg_duration_seconds', 0),
        estimatedCostUsd: j.doubleOr('estimated_usage_cost_usd', 0),
        activeAgents: j.intOr('active_agents', 0),
        runningCampaigns: j.intOr('running_campaigns', 0),
        answerRatePct: j.doubleOr('answer_rate_pct', 0),
        aiResolutionRatePct: j.doubleOr('ai_resolution_rate_pct', 0),
        humanTransferRatePct: j.doubleOr('human_transfer_rate_pct', 0),
        dailyVolume: j
            .listOfMaps('daily_volume')
            .map(DailyVolumePoint.fromJson)
            .toList(),
      );
}
