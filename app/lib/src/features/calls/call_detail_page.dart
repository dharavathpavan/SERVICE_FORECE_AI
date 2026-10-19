import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../api/api_error.dart';
import '../../api/models.dart';
import '../../platform/audio_player.dart';
import '../../services/call_stream.dart';
import '../../state/providers.dart';
import '../../theme/tokens.dart';
import '../../widgets/async_view.dart';
import '../../widgets/inputs.dart';
import '../../widgets/primitives.dart';
import '../../widgets/surfaces.dart';

class CallDetailPage extends ConsumerStatefulWidget {
  const CallDetailPage({super.key, required this.callId});

  final String callId;

  @override
  ConsumerState<CallDetailPage> createState() => _CallDetailPageState();
}

class _CallDetailPageState extends ConsumerState<CallDetailPage> {
  CallStreamClient? _stream;
  StreamSubscription<CallStreamUpdate>? _sub;
  CallStreamStatus _status = CallStreamStatus.connecting;
  String? _streamError;
  final List<CallStreamEvent> _live = <CallStreamEvent>[];
  final List<TranscriptTurn> _liveTurns = <TranscriptTurn>[];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _connect());
  }

  void _connect() {
    final String? token = ref.read(authProvider).session?.token;
    if (token == null) return;
    final CallStreamClient client =
        CallStreamClient(callId: widget.callId, token: token);
    _stream = client;
    _sub = client.updates.listen((CallStreamUpdate update) {
      if (!mounted) return;
      setState(() {
        _status = update.status;
        _streamError = update.error;
        final CallStreamEvent? e = update.event;
        if (e != null) {
          _live.add(e);
          if (e.eventType == 'transcript') {
            _liveTurns.add(
              TranscriptTurn(
                speaker: (e.payload['speaker'] ?? 'agent').toString(),
                text: (e.payload['text'] ?? '').toString(),
                startMs: 0,
                endMs: 0,
              ),
            );
          }
        }
      });
    });
    client.connect();
  }

  @override
  void dispose() {
    _sub?.cancel();
    _stream?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final AsyncValue<CallDetail> detail =
        ref.watch(callDetailProvider(widget.callId));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            AppIconButton(
              icon: Icons.arrow_back,
              onPressed: () => context.go('/app/calls'),
              semanticLabel: 'Back to calls',
              tooltip: 'Back',
            ),
            const SizedBox(width: AppSpacing.xs),
            Text('Call detail',
                style: AppType.body.copyWith(color: p.textSecondary)),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        AsyncView<CallDetail>(
          value: detail,
          onRetry: () => ref.invalidate(callDetailProvider(widget.callId)),
          skeletonLines: 8,
          isEmpty: (CallDetail _) => false,
          builder: (CallDetail d) => _Body(
            detail: d,
            live: _live,
            liveTurns: _liveTurns,
            status: _status,
            streamError: _streamError,
          ),
        ),
      ],
    );
  }
}

class _Body extends StatelessWidget {
  const _Body({
    required this.detail,
    required this.live,
    required this.liveTurns,
    required this.status,
    required this.streamError,
  });

  final CallDetail detail;
  final List<CallStreamEvent> live;
  final List<TranscriptTurn> liveTurns;
  final CallStreamStatus status;
  final String? streamError;

  @override
  Widget build(BuildContext context) {
    final CallSummary call = detail.call;
    final List<TranscriptTurn> turns = <TranscriptTurn>[
      ...detail.transcripts,
      ...liveTurns
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        PageHeader(
          eyebrow:
              call.direction == 'inbound' ? 'Inbound call' : 'Outbound call',
          title: call.callerId ?? call.phoneNumber,
          description: call.summary?.isNotEmpty == true
              ? call.summary!
              : 'No summary was produced for this call.',
          actions: <Widget>[
            statusBadgeFor(context, call.status),
            statusBadgeFor(
                context, call.outcome.isEmpty ? 'unknown' : call.outcome),
            _LiveIndicator(status: status, error: streamError),
          ],
        ),
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final bool stacked = constraints.maxWidth < 980;
            final Widget left = Column(
              children: <Widget>[
                _SummaryCard(detail: detail),
                if (detail.agentAudioUrl != null) ...<Widget>[
                  const SizedBox(height: AppSpacing.lg),
                  _AgentAudioCard(
                    callId: call.id,
                    engine: detail.agentAudioEngine,
                  ),
                ],
                const SizedBox(height: AppSpacing.lg),
                _TranscriptCard(turns: turns),
              ],
            );
            final Widget right =
                _TimelineCard(events: detail.events, live: live);
            if (stacked) {
              return Column(
                children: <Widget>[
                  left,
                  const SizedBox(height: AppSpacing.lg),
                  right,
                ],
              );
            }
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Expanded(flex: 3, child: left),
                const SizedBox(width: AppSpacing.lg),
                Expanded(flex: 2, child: right),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _LiveIndicator extends StatelessWidget {
  const _LiveIndicator({required this.status, this.error});

  final CallStreamStatus status;
  final String? error;

  @override
  Widget build(BuildContext context) {
    final (String label, AppBadgeTone tone) = switch (status) {
      CallStreamStatus.connecting => ('Live: connecting', AppBadgeTone.neutral),
      CallStreamStatus.live => ('Live', AppBadgeTone.success),
      CallStreamStatus.reconnecting => (
          'Live: reconnecting',
          AppBadgeTone.warning
        ),
      CallStreamStatus.closed => ('Live: ended', AppBadgeTone.neutral),
      CallStreamStatus.failed => ('Live: unavailable', AppBadgeTone.danger),
    };
    return Tooltip(
      message: error ?? 'Streaming call events',
      child: AppBadge(label: label, tone: tone, icon: Icons.sensors),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({required this.detail});

  final CallDetail detail;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final CallSummary c = detail.call;
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Summary',
              style: AppType.subtitle.copyWith(color: p.textPrimary)),
          const SizedBox(height: AppSpacing.sm),
          DetailRow(label: 'Number', value: c.phoneNumber, mono: true),
          DetailRow(label: 'Caller', value: c.callerId ?? '—', mono: true),
          DetailRow(label: 'Status', value: c.status),
          DetailRow(
              label: 'Outcome', value: c.outcome.isEmpty ? '—' : c.outcome),
          DetailRow(label: 'Duration', value: _duration(c.durationSeconds)),
          DetailRow(
              label: 'Estimated cost',
              value: '\$${c.estimatedCost.toStringAsFixed(3)}'),
          DetailRow(
            label: 'Started',
            value: c.createdAt == null
                ? '—'
                : DateFormat('d MMM yyyy, HH:mm:ss').format(c.createdAt!),
          ),
          if (detail.recordingUrl != null) ...<Widget>[
            const SizedBox(height: AppSpacing.sm),
            Divider(height: 1, color: p.outline),
            const SizedBox(height: AppSpacing.sm),
            Row(
              children: <Widget>[
                Icon(Icons.graphic_eq, size: 15, color: p.accent),
                const SizedBox(width: AppSpacing.xs),
                Text('Recording available',
                    style: AppType.body.copyWith(color: p.textPrimary)),
              ],
            ),
          ],
        ],
      ),
    );
  }

  static String _duration(int seconds) {
    if (seconds <= 0) return '—';
    return '${seconds ~/ 60}m ${(seconds % 60).toString().padLeft(2, '0')}s';
  }
}

class _AgentAudioCard extends ConsumerStatefulWidget {
  const _AgentAudioCard({required this.callId, this.engine});

  final String callId;
  final String? engine;

  @override
  ConsumerState<_AgentAudioCard> createState() => _AgentAudioCardState();
}

class _AgentAudioCardState extends ConsumerState<_AgentAudioCard> {
  bool _loading = false;
  bool _playing = false;
  String? _error;

  @override
  void dispose() {
    stopPlayback();
    super.dispose();
  }

  Future<void> _play() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final Uint8List bytes =
          await ref.read(callRepositoryProvider).agentAudio(widget.callId);
      if (!mounted) return;
      final String? failure = playWavBytes(bytes);
      setState(() {
        _loading = false;
        _playing = failure == null;
        _error = failure;
      });
    } on ApiError catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = e.userMessage;
      });
    }
  }

  void _stop() {
    stopPlayback();
    setState(() => _playing = false);
  }

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final String engine = switch (widget.engine) {
      'windows-sapi' => 'Windows system speech',
      'synthetic-tones' => 'synthetic speech-shaped tones',
      _ => 'a local speech engine',
    };
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(Icons.graphic_eq, size: 16, color: p.accent),
              const SizedBox(width: AppSpacing.xs),
              Text('Agent audio',
                  style: AppType.subtitle.copyWith(color: p.textPrimary)),
            ],
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            'What the AI said on this call, generated locally by the mock voice '
            'provider ($engine). Agent side only — this is not a carrier call '
            'recording.',
            style: AppType.caption.copyWith(color: p.textSecondary),
          ),
          const SizedBox(height: AppSpacing.sm),
          Row(
            children: <Widget>[
              AppButton(
                label: _playing ? 'Stop' : 'Play',
                icon: _playing ? Icons.stop : Icons.play_arrow,
                size: AppButtonSize.small,
                loading: _loading,
                tooltip: kAudioPlaybackSupported
                    ? null
                    : 'Playback is available in the web build.',
                onPressed:
                    kAudioPlaybackSupported ? (_playing ? _stop : _play) : null,
              ),
            ],
          ),
          if (_error != null) ...<Widget>[
            const SizedBox(height: AppSpacing.xs),
            Text(_error!, style: AppType.caption.copyWith(color: p.danger)),
          ],
        ],
      ),
    );
  }
}

class _TranscriptCard extends StatelessWidget {
  const _TranscriptCard({required this.turns});

  final List<TranscriptTurn> turns;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const SectionHeader(
            title: 'Transcript',
            description: 'Updates live while the call is in progress.'),
        if (turns.isEmpty)
          const AppEmptyState(
            title: 'No transcript yet',
            message: 'Turns appear here as the agent and caller speak.',
            icon: Icons.record_voice_over_outlined,
          )
        else
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                for (int i = 0; i < turns.length; i++) ...<Widget>[
                  if (i > 0) const SizedBox(height: AppSpacing.sm),
                  _TurnBubble(turn: turns[i]),
                ],
              ],
            ),
          ),
      ],
    );
  }
}

class _TurnBubble extends StatelessWidget {
  const _TurnBubble({required this.turn});

  final TranscriptTurn turn;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final Color tint = switch (turn.speaker) {
      'caller' => p.surfaceSunken,
      'system' => p.warningSurface,
      _ => p.infoSurface,
    };
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        SizedBox(
          width: 64,
          child: Text(
            turn.speaker.toUpperCase(),
            style: AppType.micro.copyWith(color: p.textTertiary),
          ),
        ),
        Expanded(
          child: Container(
            padding: const EdgeInsets.all(AppSpacing.sm),
            decoration:
                BoxDecoration(color: tint, borderRadius: AppRadii.allSm),
            child: Text(turn.text,
                style: AppType.body.copyWith(color: p.textPrimary)),
          ),
        ),
      ],
    );
  }
}

class _TimelineCard extends StatelessWidget {
  const _TimelineCard({required this.events, required this.live});

  final List<CallEventItem> events;
  final List<CallStreamEvent> live;

  @override
  Widget build(BuildContext context) {
    final int total = events.length + live.length;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        SectionHeader(
          title: 'Event timeline',
          description: '$total recorded event${total == 1 ? '' : 's'}.',
        ),
        if (total == 0)
          const AppEmptyState(
            title: 'No events recorded',
            message:
                'State transitions are logged here as the call progresses.',
            icon: Icons.timeline_outlined,
          )
        else
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                for (final CallEventItem e in events) _TimelineRow(item: e),
                for (final CallStreamEvent e in live)
                  _TimelineRow(
                    item: CallEventItem(
                        eventType: e.eventType, payload: e.payload),
                    isLive: true,
                  ),
              ],
            ),
          ),
      ],
    );
  }
}

class _TimelineRow extends StatelessWidget {
  const _TimelineRow({required this.item, this.isLive = false});

  final CallEventItem item;
  final bool isLive;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xxs),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Container(
              width: 7,
              height: 7,
              decoration: BoxDecoration(
                color: isLive ? p.accent : p.outlineStrong,
                shape: BoxShape.circle,
              ),
            ),
          ),
          const SizedBox(width: AppSpacing.xs),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Flexible(
                      child: Text(
                        item.eventType.replaceAll('_', ' '),
                        style:
                            AppType.bodyStrong.copyWith(color: p.textPrimary),
                      ),
                    ),
                    if (isLive) ...<Widget>[
                      const SizedBox(width: AppSpacing.xs),
                      const AppBadge(label: 'live', tone: AppBadgeTone.accent),
                    ],
                  ],
                ),
                if (item.payload.isNotEmpty)
                  Text(
                    _summarise(item.payload),
                    style: AppType.caption.copyWith(color: p.textSecondary),
                  ),
              ],
            ),
          ),
          if (item.createdAt != null)
            Text(DateFormat('HH:mm:ss').format(item.createdAt!),
                style: AppType.micro.copyWith(color: p.textTertiary)),
        ],
      ),
    );
  }

  static String _summarise(Map<String, dynamic> payload) {
    return payload.entries
        .where((MapEntry<String, dynamic> e) => e.value != null)
        .take(4)
        .map((MapEntry<String, dynamic> e) => '${e.key}: ${e.value}')
        .join(' · ');
  }
}
