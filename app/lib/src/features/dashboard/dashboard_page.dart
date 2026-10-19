import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../api/models.dart';
import '../../state/providers.dart';
import '../../theme/tokens.dart';
import '../../widgets/async_view.dart';
import '../../widgets/inputs.dart';
import '../../widgets/primitives.dart';
import '../../widgets/surfaces.dart';

class DashboardPage extends ConsumerWidget {
  const DashboardPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<AnalyticsOverview> analytics =
        ref.watch(analyticsProvider);
    final AsyncValue<List<CallSummary>> calls = ref.watch(callsProvider);
    final AsyncValue<CapabilityMatrix> caps =
        ref.watch(telephonyCapabilitiesProvider);
    final AuthState auth = ref.watch(authProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        PageHeader(
          eyebrow: 'Dashboard',
          title: 'Good to see you, ${_firstName(auth.session?.user.fullName)}',
          description:
              'Live view of call activity, agent resolution and telephony health.',
          actions: <Widget>[
            AppButton(
              label: 'Simulate call',
              icon: Icons.play_arrow_outlined,
              variant: AppButtonVariant.secondary,
              size: AppButtonSize.small,
              onPressed: () => context.go('/app/calls'),
            ),
            AppButton(
              label: 'New agent',
              icon: Icons.add,
              size: AppButtonSize.small,
              onPressed: () => context.go('/app/agents'),
            ),
          ],
        ),
        AsyncView<AnalyticsOverview>(
          value: analytics,
          onRetry: () => ref.invalidate(analyticsProvider),
          isEmpty: (AnalyticsOverview a) => false,
          builder: (AnalyticsOverview a) => _MetricsGrid(overview: a),
        ),
        const SizedBox(height: AppSpacing.lg),
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final bool stacked = constraints.maxWidth < 980;
            final Widget left = _RecentCalls(
                calls: calls, onRetry: () => ref.invalidate(callsProvider));
            final Widget right = _TelephonyPanel(caps: caps);
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

  static String _firstName(String? fullName) {
    if (fullName == null || fullName.trim().isEmpty) return 'there';
    return fullName.trim().split(RegExp(r'\s+')).first;
  }
}

class _MetricsGrid extends StatelessWidget {
  const _MetricsGrid({required this.overview});

  final AnalyticsOverview overview;

  @override
  Widget build(BuildContext context) {
    final List<Widget> tiles = <Widget>[
      StatTile(
        label: 'Calls today',
        value: '${overview.callsToday}',
        icon: Icons.call_outlined,
        delta: '${overview.totalCalls} in the period',
      ),
      StatTile(
        label: 'Answer rate',
        value: '${overview.answerRatePct.toStringAsFixed(0)}%',
        icon: Icons.phone_callback_outlined,
        delta: '${overview.answeredCalls} answered',
      ),
      StatTile(
        label: 'AI resolved',
        value: '${overview.aiResolutionRatePct.toStringAsFixed(0)}%',
        icon: Icons.smart_toy_outlined,
        delta: '${overview.aiResolved} handled end to end',
        deltaTone: StatDeltaTone.up,
      ),
      StatTile(
        label: 'Transferred',
        value: '${overview.humanTransferRatePct.toStringAsFixed(0)}%',
        icon: Icons.call_split_outlined,
        delta: '${overview.humanTransfers} to a human',
      ),
      StatTile(
        label: 'Avg. duration',
        value: _duration((overview.avgDurationSeconds).round()),
        icon: Icons.timer_outlined,
        delta: '${overview.totalMinutes.toStringAsFixed(0)} minutes total',
      ),
      StatTile(
        label: 'Est. usage cost',
        value: '\$${overview.estimatedCostUsd.toStringAsFixed(2)}',
        icon: Icons.receipt_outlined,
        delta: 'Estimate, not an invoice',
      ),
    ];

    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final int columns = constraints.maxWidth > 1100
            ? 3
            : (constraints.maxWidth > 720 ? 2 : 1);
        const double spacing = AppSpacing.md;
        final double width =
            (constraints.maxWidth - (spacing * (columns - 1))) / columns;
        return Wrap(
          spacing: spacing,
          runSpacing: spacing,
          children: <Widget>[
            for (final Widget tile in tiles)
              SizedBox(width: width, child: tile),
          ],
        );
      },
    );
  }

  static String _duration(int seconds) {
    if (seconds <= 0) return '—';
    final int m = seconds ~/ 60;
    final int s = seconds % 60;
    return '${m}m ${s.toString().padLeft(2, '0')}s';
  }
}

class _RecentCalls extends ConsumerWidget {
  const _RecentCalls({required this.calls, required this.onRetry});

  final AsyncValue<List<CallSummary>> calls;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        SectionHeader(
          title: 'Recent calls',
          description: 'Newest first, with the recorded outcome.',
          action: AppButton(
            label: 'View all',
            variant: AppButtonVariant.ghost,
            size: AppButtonSize.small,
            onPressed: () => context.go('/app/calls'),
          ),
        ),
        AsyncView<List<CallSummary>>(
          value: calls,
          onRetry: onRetry,
          skeletonLines: 5,
          isEmpty: (List<CallSummary> list) => list.isEmpty,
          emptyTitle: 'No calls yet',
          emptyMessage:
              'Place a test call from the Calls screen, or send an inbound call to a verified line.',
          emptyIcon: Icons.call_outlined,
          emptyAction: AppButton(
            label: 'Open calls',
            size: AppButtonSize.small,
            onPressed: () => context.go('/app/calls'),
          ),
          builder: (List<CallSummary> list) {
            final List<CallSummary> recent = list.take(6).toList();
            return AppTable(
              columns: const <AppTableColumn>[
                AppTableColumn(label: 'Caller', width: 150),
                AppTableColumn(label: 'Agent', width: 150),
                AppTableColumn(label: 'Outcome', width: 130),
                AppTableColumn(label: 'Duration', width: 100, numeric: true),
                AppTableColumn(label: 'Started', width: 150),
              ],
              rows: <TableRowData>[
                for (final CallSummary c in recent)
                  TableRowData(
                    onTap: () => context.go('/app/calls/${c.id}'),
                    cells: <Widget>[
                      Text(c.callerId ?? c.phoneNumber, style: AppType.mono),
                      Text(c.direction == 'inbound' ? 'Inbound' : 'Outbound',
                          style: AppType.body),
                      statusBadgeFor(
                          context, c.outcome.isNotEmpty ? c.outcome : c.status),
                      Text(_formatDuration(c.durationSeconds),
                          style: AppType.mono),
                      Text(_formatWhen(c.createdAt ?? c.startTime),
                          style: AppType.caption),
                    ],
                  ),
              ],
            );
          },
        ),
      ],
    );
  }

  static String _formatDuration(int seconds) {
    if (seconds <= 0) return '—';
    final int m = seconds ~/ 60;
    final int s = seconds % 60;
    return '${m}m ${s.toString().padLeft(2, '0')}s';
  }

  static String _formatWhen(DateTime? dt) {
    if (dt == null) return '—';
    return DateFormat('d MMM, HH:mm').format(dt);
  }
}

class _TelephonyPanel extends ConsumerWidget {
  const _TelephonyPanel({required this.caps});

  final AsyncValue<CapabilityMatrix> caps;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AppPalette p = context.palette;
    final AsyncValue<List<Gateway>> gateways = ref.watch(gatewaysProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        SectionHeader(
          title: 'Telephony',
          description:
              'What the configured provider supports, and gateway state.',
          action: AppButton(
            label: 'Gateways',
            variant: AppButtonVariant.ghost,
            size: AppButtonSize.small,
            onPressed: () => context.go('/app/gateways'),
          ),
        ),
        AsyncView<CapabilityMatrix>(
          value: caps,
          onRetry: () => ref.invalidate(telephonyCapabilitiesProvider),
          skeletonLines: 6,
          isEmpty: (CapabilityMatrix _) => false,
          builder: (CapabilityMatrix c) => Column(
            children: <Widget>[
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      children: <Widget>[
                        Text('Provider',
                            style: AppType.caption
                                .copyWith(color: p.textSecondary)),
                        const Spacer(),
                        AppBadge(label: c.provider, tone: AppBadgeTone.accent),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    for (final MapEntry<String, String> e
                        in c.capabilities.entries)
                      _CapabilityRow(name: e.key, value: e.value),
                    if (c.notes.isNotEmpty) ...<Widget>[
                      const SizedBox(height: AppSpacing.sm),
                      Divider(height: 1, color: p.outline),
                      const SizedBox(height: AppSpacing.sm),
                      for (final String note in c.notes)
                        Padding(
                          padding:
                              const EdgeInsets.only(bottom: AppSpacing.xxs),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Icon(Icons.info_outline,
                                  size: 13, color: p.textTertiary),
                              const SizedBox(width: AppSpacing.xxs),
                              Expanded(
                                child: Text(note,
                                    style: AppType.caption
                                        .copyWith(color: p.textTertiary)),
                              ),
                            ],
                          ),
                        ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              AsyncView<List<Gateway>>(
                value: gateways,
                onRetry: () => ref.invalidate(gatewaysProvider),
                isEmpty: (List<Gateway> list) => list.isEmpty,
                emptyTitle: 'No gateways registered',
                emptyMessage:
                    'Register a SIP endpoint to connect a SIM-backed voice gateway.',
                emptyIcon: Icons.router_outlined,
                builder: (List<Gateway> list) => AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text('Gateways',
                          style: AppType.bodyStrong
                              .copyWith(color: p.textPrimary)),
                      const SizedBox(height: AppSpacing.sm),
                      for (final Gateway g in list)
                        Padding(
                          padding: const EdgeInsets.only(bottom: AppSpacing.xs),
                          child: Row(
                            children: <Widget>[
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: <Widget>[
                                    Text(g.identifier,
                                        style: AppType.body
                                            .copyWith(color: p.textPrimary)),
                                    Text(g.sipEndpoint,
                                        style: AppType.caption
                                            .copyWith(color: p.textTertiary)),
                                  ],
                                ),
                              ),
                              statusBadgeFor(context, g.status.name),
                            ],
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _CapabilityRow extends StatelessWidget {
  const _CapabilityRow({required this.name, required this.value});

  final String name;
  final String value;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final String label = name
        .split('_')
        .where((String w) => w.isNotEmpty)
        .map((String w) => '${w[0].toUpperCase()}${w.substring(1)}')
        .join(' ');
    final AppBadgeTone tone = switch (value) {
      'supported' => AppBadgeTone.success,
      'unsupported' => AppBadgeTone.danger,
      _ => AppBadgeTone.neutral,
    };
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: <Widget>[
          Expanded(
              child: Text(label,
                  style: AppType.body.copyWith(color: p.textSecondary))),
          AppBadge(label: value, tone: tone),
        ],
      ),
    );
  }
}
