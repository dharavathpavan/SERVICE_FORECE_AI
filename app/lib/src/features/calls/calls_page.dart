import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../api/models.dart';
import '../../state/providers.dart';
import '../../theme/tokens.dart';
import '../../widgets/async_view.dart';
import '../../widgets/dialpad.dart';
import '../../widgets/inputs.dart';
import '../../widgets/primitives.dart';
import '../../widgets/surfaces.dart';

enum _CallFilter {
  all('All'),
  inbound('Inbound'),
  outbound('Outbound'),
  completed('Completed'),
  failed('Failed');

  const _CallFilter(this.label);
  final String label;
}

class CallsPage extends ConsumerStatefulWidget {
  const CallsPage({super.key});

  @override
  ConsumerState<CallsPage> createState() => _CallsPageState();
}

class _CallsPageState extends ConsumerState<CallsPage> {
  _CallFilter _filter = _CallFilter.all;

  @override
  Widget build(BuildContext context) {
    final AsyncValue<List<CallSummary>> calls = ref.watch(callsProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        PageHeader(
          eyebrow: 'Calls',
          title: 'Call activity',
          description:
              'Every call with its recorded outcome. Nothing is marked successful unless it was.',
          actions: <Widget>[
            AppButton(
              label: 'Simulate inbound',
              icon: Icons.science_outlined,
              variant: AppButtonVariant.secondary,
              size: AppButtonSize.small,
              onPressed: () => _showSimulateDialog(context),
            ),
            AppButton(
              label: 'Place call',
              icon: Icons.add_ic_call_outlined,
              size: AppButtonSize.small,
              onPressed: () => _showDialDialog(context),
            ),
          ],
        ),
        Wrap(
          spacing: AppSpacing.xs,
          runSpacing: AppSpacing.xs,
          children: <Widget>[
            for (final _CallFilter f in _CallFilter.values)
              _FilterChip(
                label: f.label,
                selected: _filter == f,
                onTap: () => setState(() => _filter = f),
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        AsyncView<List<CallSummary>>(
          value: calls,
          onRetry: () => ref.invalidate(callsProvider),
          skeletonLines: 6,
          isEmpty: (List<CallSummary> list) => _apply(list).isEmpty,
          emptyTitle: 'No calls match this filter',
          emptyMessage:
              'Simulate an inbound call to exercise the agent end to end, or place an outbound call to a number.',
          emptyIcon: Icons.call_outlined,
          emptyAction: AppButton(
            label: 'Simulate inbound call',
            size: AppButtonSize.small,
            onPressed: () => _showSimulateDialog(context),
          ),
          builder: (List<CallSummary> list) {
            final List<CallSummary> rows = _apply(list);
            return AppTable(
              columns: const <AppTableColumn>[
                AppTableColumn(label: 'Caller', width: 150),
                AppTableColumn(label: 'Number', width: 150),
                AppTableColumn(label: 'Direction', width: 110),
                AppTableColumn(label: 'Status', width: 120),
                AppTableColumn(label: 'Outcome', width: 130),
                AppTableColumn(label: 'Duration', width: 96, numeric: true),
                AppTableColumn(label: 'Cost', width: 84, numeric: true),
                AppTableColumn(label: 'Started', width: 150),
              ],
              rows: <TableRowData>[
                for (final CallSummary c in rows)
                  TableRowData(
                    onTap: () => context.go('/app/calls/${c.id}'),
                    cells: <Widget>[
                      Text(c.callerId ?? '—', style: AppType.mono),
                      Text(c.phoneNumber, style: AppType.mono),
                      Text(c.direction == 'inbound' ? 'Inbound' : 'Outbound',
                          style: AppType.body),
                      statusBadgeFor(context, c.status),
                      statusBadgeFor(
                          context, c.outcome.isEmpty ? 'unknown' : c.outcome),
                      Text(_duration(c.durationSeconds), style: AppType.mono),
                      Text('\$${c.estimatedCost.toStringAsFixed(3)}',
                          style: AppType.mono),
                      Text(_when(c.createdAt ?? c.startTime),
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

  List<CallSummary> _apply(List<CallSummary> list) {
    switch (_filter) {
      case _CallFilter.all:
        return list;
      case _CallFilter.inbound:
        return list.where((CallSummary c) => c.direction == 'inbound').toList();
      case _CallFilter.outbound:
        return list
            .where((CallSummary c) => c.direction == 'outbound')
            .toList();
      case _CallFilter.completed:
        return list.where((CallSummary c) => c.status == 'completed').toList();
      case _CallFilter.failed:
        return list.where((CallSummary c) => c.status == 'failed').toList();
    }
  }

  static String _duration(int seconds) {
    if (seconds <= 0) return '—';
    return '${seconds ~/ 60}m ${(seconds % 60).toString().padLeft(2, '0')}s';
  }

  static String _when(DateTime? dt) =>
      dt == null ? '—' : DateFormat('d MMM, HH:mm').format(dt);

  Future<void> _showSimulateDialog(BuildContext context) async {
    await showDialog<void>(
      context: context,
      builder: (BuildContext context) => const _SimulateCallDialog(),
    );
  }

  Future<void> _showDialDialog(BuildContext context) async {
    await showDialog<void>(
      context: context,
      builder: (BuildContext context) => const _DialDialog(),
    );
  }
}

class _FilterChip extends StatelessWidget {
  const _FilterChip(
      {required this.label, required this.selected, required this.onTap});

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Material(
      color: selected ? p.infoSurface : p.surface,
      borderRadius: AppRadii.allSm,
      child: InkWell(
        onTap: onTap,
        borderRadius: AppRadii.allSm,
        child: Container(
          padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.sm, vertical: AppSpacing.xs),
          decoration: BoxDecoration(
            borderRadius: AppRadii.allSm,
            border: Border.all(
                color: selected ? p.accent.withValues(alpha: 0.4) : p.outline),
          ),
          child: Text(
            label,
            style: AppType.label
                .copyWith(color: selected ? p.accent : p.textSecondary),
          ),
        ),
      ),
    );
  }
}

class _SimulateCallDialog extends ConsumerStatefulWidget {
  const _SimulateCallDialog();

  @override
  ConsumerState<_SimulateCallDialog> createState() =>
      _SimulateCallDialogState();
}

class _SimulateCallDialogState extends ConsumerState<_SimulateCallDialog> {
  String _scenario = 'order_tracking';
  bool _busy = false;
  Map<String, dynamic>? _result;
  Object? _error;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Dialog(
      backgroundColor: p.surface,
      shape: const RoundedRectangleBorder(borderRadius: AppRadii.allMd),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 460),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Simulate an inbound call',
                  style: AppType.subtitle.copyWith(color: p.textPrimary)),
              const SizedBox(height: AppSpacing.xxs),
              Text(
                'Runs the full agent pipeline against the mock voice provider. No carrier traffic is generated.',
                style: AppType.body.copyWith(color: p.textSecondary),
              ),
              const SizedBox(height: AppSpacing.md),
              AppSelect<String>(
                label: 'Scenario',
                value: _scenario,
                items: const <DropdownMenuItem<String>>[
                  DropdownMenuItem<String>(
                      value: 'order_tracking', child: Text('Order tracking')),
                  DropdownMenuItem<String>(
                      value: 'appointment_booking',
                      child: Text('Appointment booking')),
                  DropdownMenuItem<String>(
                      value: 'faq_inquiry', child: Text('FAQ enquiry')),
                  DropdownMenuItem<String>(
                      value: 'human_escalation',
                      child: Text('Human escalation')),
                ],
                onChanged: (String? v) =>
                    setState(() => _scenario = v ?? _scenario),
              ),
              if (_error != null) ...<Widget>[
                const SizedBox(height: AppSpacing.md),
                InlineError(error: _error!),
              ],
              if (_result != null) ...<Widget>[
                const SizedBox(height: AppSpacing.md),
                InlineNotice(
                  tone: NoticeTone.success,
                  message:
                      'Call ${_result!['status']}: ${_result!['summary'] ?? 'completed'}',
                ),
              ],
              const SizedBox(height: AppSpacing.lg),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: <Widget>[
                  AppButton(
                    label: 'Close',
                    variant: AppButtonVariant.ghost,
                    size: AppButtonSize.small,
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                  const SizedBox(width: AppSpacing.xs),
                  AppButton(
                    label: 'Run simulation',
                    size: AppButtonSize.small,
                    loading: _busy,
                    onPressed: _busy
                        ? null
                        : () async {
                            setState(() {
                              _busy = true;
                              _error = null;
                              _result = null;
                            });
                            try {
                              final Map<String, dynamic> r = await ref
                                  .read(callRepositoryProvider)
                                  .simulate(scenario: _scenario);
                              ref.invalidate(callsProvider);
                              ref.invalidate(analyticsProvider);
                              if (mounted) setState(() => _result = r);
                            } catch (e) {
                              if (mounted) setState(() => _error = e);
                            } finally {
                              if (mounted) setState(() => _busy = false);
                            }
                          },
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DialDialog extends ConsumerStatefulWidget {
  const _DialDialog();

  @override
  ConsumerState<_DialDialog> createState() => _DialDialogState();
}

class _DialDialogState extends ConsumerState<_DialDialog> {
  final TextEditingController _to = TextEditingController();
  String? _connectionId;
  String? _agentId;
  final TextEditingController _reason = TextEditingController();
  bool _confirmed = false;
  bool _busy = false;
  Object? _error;
  Map<String, dynamic>? _result;

  @override
  void initState() {
    super.initState();
    // Rebuild as the number changes, so the keypad and "Place call" state are
    // always in step with the field (including physical keyboard typing).
    _to.addListener(_onNumberChanged);
    // Preselect the first verified line and agent for convenience.
    final List<PhoneConnection>? lines =
        ref.read(phoneConnectionsProvider).valueOrNull;
    if (lines != null && lines.isNotEmpty) {
      _connectionId = lines
          .firstWhere(
            (PhoneConnection c) => c.isVerified,
            orElse: () => lines.first,
          )
          .id;
    }
    final List<Agent>? agents = ref.read(agentsProvider).valueOrNull;
    if (agents != null && agents.isNotEmpty) _agentId = agents.first.id;
  }

  @override
  void dispose() {
    _to.removeListener(_onNumberChanged);
    _to.dispose();
    _reason.dispose();
    super.dispose();
  }

  void _onNumberChanged() {
    if (mounted) setState(() {});
  }

  void _append(String digit) {
    _to.text = '${_to.text}$digit';
    _to.selection = TextSelection.collapsed(offset: _to.text.length);
  }

  void _backspace() {
    if (_to.text.isEmpty) return;
    _to.text = _to.text.substring(0, _to.text.length - 1);
    _to.selection = TextSelection.collapsed(offset: _to.text.length);
  }

  void _clear() => _to.clear();

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final List<PhoneConnection> lines =
        ref.watch(phoneConnectionsProvider).valueOrNull ?? <PhoneConnection>[];
    final List<Agent> agents =
        ref.watch(agentsProvider).valueOrNull ?? <Agent>[];

    return Dialog(
      backgroundColor: p.surface,
      shape: const RoundedRectangleBorder(borderRadius: AppRadii.allMd),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 480),
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('Place an outbound call',
                    style: AppType.subtitle.copyWith(color: p.textPrimary)),
                const SizedBox(height: AppSpacing.xxs),
                Text(
                  'Server-side policy gates still apply: calling hours, suppression, consent, monthly cap '
                  'and concurrency are checked before anything is dialled.',
                  style: AppType.body.copyWith(color: p.textSecondary),
                ),
                const SizedBox(height: AppSpacing.md),
                AppTextField(
                  label: 'Destination number',
                  controller: _to,
                  hint: '+1 555 0100',
                  prefixIcon: Icons.dialpad_outlined,
                  keyboardType: TextInputType.phone,
                ),
                const SizedBox(height: AppSpacing.xs),
                Dialpad(onKey: _append, enabled: !_busy),
                const SizedBox(height: AppSpacing.xs),
                Row(
                  children: <Widget>[
                    AppButton(
                      label: 'Backspace',
                      icon: Icons.backspace_outlined,
                      variant: AppButtonVariant.ghost,
                      size: AppButtonSize.small,
                      onPressed: _to.text.isEmpty ? null : _backspace,
                    ),
                    const SizedBox(width: AppSpacing.xxs),
                    AppButton(
                      label: 'Clear',
                      variant: AppButtonVariant.ghost,
                      size: AppButtonSize.small,
                      onPressed: _to.text.isEmpty ? null : _clear,
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.sm),
                AppSelect<String?>(
                  label: 'Calling line',
                  value: _connectionId,
                  items: <DropdownMenuItem<String?>>[
                    const DropdownMenuItem<String?>(
                        value: null, child: Text('Default line')),
                    for (final PhoneConnection c in lines)
                      DropdownMenuItem<String?>(
                        value: c.id,
                        child: Text(
                            '${c.friendlyName} · ${c.phoneNumber}${c.isVerified ? '' : ' (unverified)'}'),
                      ),
                  ],
                  onChanged: (String? v) => setState(() => _connectionId = v),
                  helper: lines.any((PhoneConnection c) => !c.isVerified)
                      ? 'Unverified lines will be blocked by policy.'
                      : null,
                ),
                const SizedBox(height: AppSpacing.sm),
                AppSelect<String?>(
                  label: 'Agent',
                  value: _agentId,
                  items: <DropdownMenuItem<String?>>[
                    const DropdownMenuItem<String?>(
                        value: null, child: Text('No agent')),
                    for (final Agent a in agents)
                      DropdownMenuItem<String?>(
                          value: a.id, child: Text(a.name)),
                  ],
                  onChanged: (String? v) => setState(() => _agentId = v),
                ),
                const SizedBox(height: AppSpacing.sm),
                AppTextField(
                  label: 'Reason (optional)',
                  controller: _reason,
                  hint: 'Follow-up on a support ticket',
                ),
                const SizedBox(height: AppSpacing.sm),
                AppSwitchRow(
                  title: 'Confirm this call',
                  description:
                      'Required. Confirms you have a lawful basis to call this number.',
                  value: _confirmed,
                  onChanged: (bool v) => setState(() => _confirmed = v),
                ),
                if (_error != null) ...<Widget>[
                  const SizedBox(height: AppSpacing.md),
                  InlineError(error: _error!),
                ],
                if (_result != null) ...<Widget>[
                  const SizedBox(height: AppSpacing.md),
                  InlineNotice(
                    tone: _result!['action'] == 'initiated'
                        ? NoticeTone.success
                        : NoticeTone.warning,
                    message:
                        _result!['message']?.toString() ?? 'Call processed.',
                  ),
                ],
                if (_result != null && _result!['call_id'] != null) ...<Widget>[
                  const SizedBox(height: AppSpacing.xs),
                  AppButton(
                    label: 'Open call',
                    icon: Icons.open_in_new,
                    variant: AppButtonVariant.secondary,
                    size: AppButtonSize.small,
                    onPressed: () {
                      final String callId = _result!['call_id'].toString();
                      Navigator.of(context).pop();
                      context.go('/app/calls/$callId');
                    },
                  ),
                ],
                const SizedBox(height: AppSpacing.lg),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: <Widget>[
                    AppButton(
                      label: 'Cancel',
                      variant: AppButtonVariant.ghost,
                      size: AppButtonSize.small,
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                    const SizedBox(width: AppSpacing.xs),
                    AppButton(
                      label: 'Place call',
                      size: AppButtonSize.small,
                      loading: _busy,
                      onPressed: _busy || !_confirmed || _to.text.trim().isEmpty
                          ? null
                          : () async {
                              setState(() {
                                _busy = true;
                                _error = null;
                                _result = null;
                              });
                              try {
                                final Map<String, dynamic> r = await ref
                                    .read(callRepositoryProvider)
                                    .placeOutbound(
                                      toNumber: _to.text.trim(),
                                      connectionId: _connectionId,
                                      agentId: _agentId,
                                      reason: _reason.text.trim().isEmpty
                                          ? null
                                          : _reason.text.trim(),
                                    );
                                ref.invalidate(callsProvider);
                                if (mounted) setState(() => _result = r);
                              } catch (e) {
                                if (mounted) setState(() => _error = e);
                              } finally {
                                if (mounted) setState(() => _busy = false);
                              }
                            },
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
