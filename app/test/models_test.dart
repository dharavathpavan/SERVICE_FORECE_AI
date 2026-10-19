import 'package:flutter_test/flutter_test.dart';
import 'package:serviceforce/src/api/models.dart';

/// The API client parses untrusted JSON. These tests pin the defensive behaviour:
/// missing or mistyped fields must fall back rather than throw.

void main() {
  group('AuthSession.fromJson', () {
    test('parses a full login response', () {
      final AuthSession session = AuthSession.fromJson(<String, dynamic>{
        'access_token': 'tok_123',
        'organization_id': 'org_1',
        'organization_name': 'Clean Slate Clinic',
        'role': 'owner',
        'user': <String, dynamic>{
          'id': 'usr_1',
          'email': 'owner@example.com',
          'full_name': 'Dana Owner',
          'is_active': true,
        },
      });

      expect(session.token, 'tok_123');
      expect(session.organizationName, 'Clean Slate Clinic');
      expect(session.role, 'owner');
      expect(session.user.fullName, 'Dana Owner');
    });

    test('falls back instead of throwing on an empty payload', () {
      final AuthSession session = AuthSession.fromJson(<String, dynamic>{});
      expect(session.token, isEmpty);
      expect(session.role, 'operator');
      expect(session.user.fullName, 'Unknown user');
    });
  });

  group('Agent', () {
    test('defaults an unknown direction to "both" and keeps the parsed value',
        () {
      expect(
          Agent.fromJson(<String, dynamic>{'direction': 'sideways'}).direction,
          AgentDirection.both);
      expect(
          Agent.fromJson(<String, dynamic>{'direction': 'inbound'}).direction,
          AgentDirection.inbound);
    });

    test('is safe when optional fields are absent', () {
      final Agent agent = Agent.fromJson(<String, dynamic>{'name': 'Support'});
      expect(agent.name, 'Support');
      expect(agent.humanTransferNumber, isNull);
      expect(agent.maxDurationSeconds, 600);
      expect(agent.isActive, isTrue);
    });
  });

  group('Gateway', () {
    test('never reports a gateway as verified without an explicit status', () {
      final Gateway gateway =
          Gateway.fromJson(<String, dynamic>{'identifier': 'gw-1'});
      expect(gateway.status, GatewayStatus.unverified);
      expect(gateway.connected, isFalse);
      expect(gateway.needsVerification, isTrue);
    });

    test('parses a probe payload with line detail', () {
      final GatewayProbe probe = GatewayProbe.fromJson(<String, dynamic>{
        'ok': true,
        'status': 'online',
        'message': 'Probe succeeded',
        'latency_ms': 42.5,
        'lines': <dynamic>[
          <String, dynamic>{
            'line_id': 'line-1',
            'state': 'registered',
            'usable': true,
            'registration_ok': true,
            'sim_present': true,
            'signal_percent': 82,
            'active_channels': 0,
          },
        ],
      });

      expect(probe.ok, isTrue);
      expect(probe.latencyMs, 42.5);
      expect(probe.lines, hasLength(1));
      expect(probe.lines.first.usable, isTrue);
      expect(probe.lines.first.signalPercent, 82);
    });

    test('treats a failed probe honestly, without inventing lines', () {
      final GatewayProbe probe = GatewayProbe.fromJson(<String, dynamic>{
        'ok': false,
        'status': 'offline',
        'message': 'Gateway unreachable',
      });
      expect(probe.ok, isFalse);
      expect(probe.lines, isEmpty);
      expect(probe.status, 'offline');
    });
  });

  group('CallSummary', () {
    test('keeps failed calls labelled as failed with zero duration', () {
      final CallSummary call = CallSummary.fromJson(<String, dynamic>{
        'id': 'call_1',
        'phone_number': '+15550142',
        'direction': 'outbound',
        'status': 'failed',
        'outcome': 'carrier_error',
        'duration_seconds': 0,
        'estimated_cost': 0,
      });

      expect(call.status, 'failed');
      expect(call.outcome, 'carrier_error');
      expect(call.durationSeconds, 0);
      expect(call.estimatedCost, 0);
    });
  });

  group('AnalyticsOverview', () {
    test('defaults every counter to zero when the payload is empty', () {
      final AnalyticsOverview overview =
          AnalyticsOverview.fromJson(<String, dynamic>{});
      expect(overview.totalCalls, 0);
      expect(overview.answerRatePct, 0);
      expect(overview.dailyVolume, isEmpty);
    });

    test('parses the daily volume series', () {
      final AnalyticsOverview overview =
          AnalyticsOverview.fromJson(<String, dynamic>{
        'total_calls': 12,
        'answer_rate_pct': 75.5,
        'daily_volume': <dynamic>[
          <String, dynamic>{
            'label': 'Oct 01',
            'total_calls': 3,
            'ai_resolved': 2,
            'transferred': 1
          },
        ],
      });

      expect(overview.totalCalls, 12);
      expect(overview.answerRatePct, 75.5);
      expect(overview.dailyVolume.single.label, 'Oct 01');
      expect(overview.dailyVolume.single.aiResolved, 2);
    });
  });
}
