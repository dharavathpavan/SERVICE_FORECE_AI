import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../api/models.dart';
import '../../state/providers.dart';
import '../../theme/tokens.dart';
import '../../widgets/async_view.dart';
import '../../widgets/inputs.dart';
import '../../widgets/primitives.dart';
import '../../widgets/surfaces.dart';

class AnalyticsPage extends ConsumerWidget {
  const AnalyticsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AppPalette p = context.palette;
    final AsyncValue<AnalyticsOverview> analytics =
        ref.watch(analyticsProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        PageHeader(
          eyebrow: 'Insights',
          title: 'Analytics',
          description:
              'Outcomes are counted separately so the numbers stay honest: answered, resolved, transferred and failed '
              'are never merged.',
          actions: <Widget>[
            AppButton(
              label: 'Refresh',
              icon: Icons.refresh,
              variant: AppButtonVariant.secondary,
              size: AppButtonSize.small,
              onPressed: () => ref.invalidate(analyticsProvider),
            ),
          ],
        ),
        AsyncView<AnalyticsOverview>(
          value: analytics,
          onRetry: () => ref.invalidate(analyticsProvider),
          skeletonLines: 8,
          isEmpty: (AnalyticsOverview a) =>
              a.totalCalls == 0 && a.callsToday == 0,
          emptyTitle: 'No call data in this period',
          emptyMessage:
              'Place or receive a call and the metrics here will populate. Nothing is estimated until there is data.',
          emptyIcon: Icons.insights_outlined,
          builder: (AnalyticsOverview a) => Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              LayoutBuilder(
                builder: (BuildContext context, BoxConstraints constraints) {
                  final int columns = constraints.maxWidth > 1100
                      ? 4
                      : (constraints.maxWidth > 720 ? 2 : 1);
                  const double spacing = AppSpacing.md;
                  final double width =
                      (constraints.maxWidth - (spacing * (columns - 1))) /
                          columns;
                  final List<Widget> tiles = <Widget>[
                    StatTile(
                      label: 'Total calls (30d)',
                      value: '${a.totalCalls}',
                      icon: Icons.call_outlined,
                      delta: '${a.callsToday} today',
                    ),
                    StatTile(
                      label: 'Answered',
                      value: '${a.answeredCalls}',
                      icon: Icons.phone_callback_outlined,
                      delta:
                          '${a.answerRatePct.toStringAsFixed(1)}% of attempts',
                    ),
                    StatTile(
                      label: 'AI resolved',
                      value: '${a.aiResolved}',
                      icon: Icons.smart_toy_outlined,
                      delta:
                          '${a.aiResolutionRatePct.toStringAsFixed(1)}% of answered',
                      deltaTone: StatDeltaTone.up,
                    ),
                    StatTile(
                      label: 'Transferred to human',
                      value: '${a.humanTransfers}',
                      icon: Icons.call_split_outlined,
                      delta:
                          '${a.humanTransferRatePct.toStringAsFixed(1)}% of answered',
                    ),
                    StatTile(
                      label: 'Failed / unanswered',
                      value: '${a.failedCalls}',
                      icon: Icons.phone_missed_outlined,
                      delta: 'Busy, no answer or rejected',
                      deltaTone: StatDeltaTone.down,
                    ),
                    StatTile(
                      label: 'Average duration',
                      value: _duration(a.avgDurationSeconds.round()),
                      icon: Icons.timer_outlined,
                      delta:
                          '${a.totalMinutes.toStringAsFixed(1)} minutes total',
                    ),
                    StatTile(
                      label: 'Active agents',
                      value: '${a.activeAgents}',
                      icon: Icons.smart_toy_outlined,
                    ),
                    StatTile(
                      label: 'Running campaigns',
                      value: '${a.runningCampaigns}',
                      icon: Icons.campaign_outlined,
                      delta: a.estimatedCostUsd > 0
                          ? 'Est. cost \$${a.estimatedCostUsd.toStringAsFixed(2)}'
                          : 'No billable usage yet',
                    ),
                  ];
                  return Wrap(
                    spacing: spacing,
                    runSpacing: spacing,
                    children: <Widget>[
                      for (final Widget t in tiles)
                        SizedBox(width: width, child: t),
                    ],
                  );
                },
              ),
              const SizedBox(height: AppSpacing.lg),
              const SectionHeader(
                title: 'Call volume, last 7 days',
                description:
                    'Bars show total calls per day. Hover a bar for the resolved and transferred split.',
              ),
              AppCard(
                padding: const EdgeInsets.all(AppSpacing.lg),
                child: a.dailyVolume.isEmpty
                    ? Text(
                        'No daily data points available yet.',
                        style: AppType.body.copyWith(color: p.textSecondary),
                      )
                    : _DailyVolumeChart(points: a.dailyVolume),
              ),
              const SizedBox(height: AppSpacing.md),
              Row(
                children: <Widget>[
                  Icon(Icons.info_outline, size: 14, color: p.textTertiary),
                  const SizedBox(width: AppSpacing.xs),
                  Expanded(
                    child: Text(
                      'Usage cost is an estimate derived from call duration and configured rates. It is not an invoice.',
                      style: AppType.caption.copyWith(color: p.textTertiary),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }

  static String _duration(int seconds) {
    if (seconds <= 0) return '—';
    return '${seconds ~/ 60}m ${(seconds % 60).toString().padLeft(2, '0')}s';
  }
}

class _DailyVolumeChart extends StatelessWidget {
  const _DailyVolumeChart({required this.points});

  final List<DailyVolumePoint> points;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final int max = points.fold<int>(
        1, (int m, DailyVolumePoint x) => x.totalCalls > m ? x.totalCalls : m);
    const double chartHeight = 180;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        SizedBox(
          height: chartHeight + 34,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: <Widget>[
              for (final DailyVolumePoint point in points)
                Expanded(
                  child: Padding(
                    padding:
                        const EdgeInsets.symmetric(horizontal: AppSpacing.xxs),
                    child: Tooltip(
                      message: '${point.label}\n'
                          'Total: ${point.totalCalls}\n'
                          'AI resolved: ${point.aiResolved}\n'
                          'Transferred: ${point.transferred}',
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: <Widget>[
                          Text(
                            '${point.totalCalls}',
                            style: AppType.caption
                                .copyWith(color: p.textSecondary),
                          ),
                          const SizedBox(height: AppSpacing.xxs),
                          Container(
                            height: 8 +
                                (chartHeight - 8) * (point.totalCalls / max),
                            decoration: BoxDecoration(
                              color: point.totalCalls == 0
                                  ? p.surfaceVariant
                                  : p.accent,
                              borderRadius: const BorderRadius.vertical(
                                top: Radius.circular(4),
                                bottom: Radius.circular(2),
                              ),
                            ),
                          ),
                          const SizedBox(height: AppSpacing.xs),
                          Text(
                            point.label,
                            style:
                                AppType.micro.copyWith(color: p.textTertiary),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        Divider(height: 1, color: p.outline),
        const SizedBox(height: AppSpacing.md),
        AppTable(
          columns: const <AppTableColumn>[
            AppTableColumn(label: 'Day', width: 140),
            AppTableColumn(label: 'Total calls', width: 120, numeric: true),
            AppTableColumn(label: 'AI resolved', width: 120, numeric: true),
            AppTableColumn(label: 'Transferred', width: 120, numeric: true),
            AppTableColumn(label: 'Resolved %', width: 120, numeric: true),
          ],
          rows: <TableRowData>[
            for (final DailyVolumePoint point in points)
              TableRowData(
                cells: <Widget>[
                  Text(point.label,
                      style: AppType.body.copyWith(color: p.textPrimary)),
                  Text('${point.totalCalls}', style: AppType.mono),
                  Text('${point.aiResolved}', style: AppType.mono),
                  Text('${point.transferred}', style: AppType.mono),
                  Text(
                    point.totalCalls == 0
                        ? '—'
                        : '${(point.aiResolved / point.totalCalls * 100).toStringAsFixed(0)}%',
                    style: AppType.mono,
                  ),
                ],
              ),
          ],
        ),
      ],
    );
  }
}
