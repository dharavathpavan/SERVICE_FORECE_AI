import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../api/models.dart';
import '../../state/providers.dart';
import '../../theme/tokens.dart';
import '../../widgets/async_view.dart';
import '../../widgets/inputs.dart';
import '../../widgets/primitives.dart';
import '../../widgets/surfaces.dart';

class GatewaysPage extends ConsumerWidget {
  const GatewaysPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AppPalette p = context.palette;
    final AsyncValue<List<Gateway>> gateways = ref.watch(gatewaysProvider);
    final AsyncValue<CapabilityMatrix> caps =
        ref.watch(telephonyCapabilitiesProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        PageHeader(
          eyebrow: 'Telephony',
          title: 'Gateways',
          description:
              'A gateway is only marked online after an active probe succeeds. Nothing is assumed.',
          actions: <Widget>[
            AppButton(
              label: 'Register gateway',
              icon: Icons.add,
              size: AppButtonSize.small,
              onPressed: () => _showRegisterDialog(context, ref),
            ),
          ],
        ),
        AsyncView<CapabilityMatrix>(
          value: caps,
          onRetry: () => ref.invalidate(telephonyCapabilitiesProvider),
          skeletonLines: 3,
          isEmpty: (CapabilityMatrix _) => false,
          builder: (CapabilityMatrix c) => Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.md),
            child: InlineNotice(
              tone: c.provider == 'mock' ? NoticeTone.info : NoticeTone.success,
              message: c.provider == 'mock'
                  ? 'Provider is "mock": registrations and probes are simulated. Set TELEPHONY_PROVIDER to '
                      '"asterisk" and configure ARI to control a real PBX.'
                  : 'Provider "${c.provider}" is active. Probes reflect the real PBX.',
            ),
          ),
        ),
        AsyncView<List<Gateway>>(
          value: gateways,
          onRetry: () => ref.invalidate(gatewaysProvider),
          skeletonLines: 6,
          isEmpty: (List<Gateway> list) => list.isEmpty,
          emptyTitle: 'No gateways registered',
          emptyMessage:
              'Add the SIP endpoint of your GSM/VoLTE gateway. It will stay unverified until a probe succeeds.',
          emptyIcon: Icons.router_outlined,
          emptyAction: AppButton(
            label: 'Register a gateway',
            size: AppButtonSize.small,
            onPressed: () => _showRegisterDialog(context, ref),
          ),
          builder: (List<Gateway> list) => Column(
            children: <Widget>[
              for (final Gateway g in list)
                Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.md),
                  child: _GatewayCard(gateway: g),
                ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        _SetupNote(),
        const SizedBox(height: AppSpacing.md),
        Align(
          alignment: Alignment.centerLeft,
          child: Text(
            'Consumer phones do not expose low-latency full-duplex audio, so they cannot act as a gateway. '
            'Use a dedicated GSM/VoLTE gateway.',
            style: AppType.caption.copyWith(color: p.textTertiary),
          ),
        ),
      ],
    );
  }

  static Future<void> _showRegisterDialog(
      BuildContext context, WidgetRef ref) async {
    await showDialog<void>(
      context: context,
      builder: (BuildContext context) => const _RegisterGatewayDialog(),
    );
  }
}

class _GatewayCard extends ConsumerStatefulWidget {
  const _GatewayCard({required this.gateway});

  final Gateway gateway;

  @override
  ConsumerState<_GatewayCard> createState() => _GatewayCardState();
}

class _GatewayCardState extends ConsumerState<_GatewayCard> {
  bool _expanded = false;
  bool _verifying = false;
  GatewayProbe? _probe;
  Object? _error;
  List<GatewayLine> _lines = <GatewayLine>[];
  bool _loadingLines = false;

  Future<void> _verify() async {
    setState(() {
      _verifying = true;
      _error = null;
      _probe = null;
    });
    try {
      final ({Gateway gateway, GatewayProbe probe}) r = await ref
          .read(telephonyRepositoryProvider)
          .verifyGateway(widget.gateway.id);
      ref.invalidate(gatewaysProvider);
      if (mounted) {
        setState(() {
          _probe = r.probe;
          _lines = r.probe.lines;
          _expanded = true;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _verifying = false);
    }
  }

  Future<void> _loadLines() async {
    setState(() {
      _loadingLines = true;
      _error = null;
    });
    try {
      final List<GatewayLine> lines =
          await ref.read(telephonyRepositoryProvider).lines(widget.gateway.id);
      if (mounted) setState(() => _lines = lines);
    } catch (e) {
      if (mounted) setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _loadingLines = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final Gateway g = widget.gateway;
    final Map<String, dynamic> health = g.healthDetails;

    return AppCard(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                    color: p.surfaceVariant, borderRadius: AppRadii.allSm),
                child: Icon(Icons.router_outlined,
                    size: 17, color: p.textSecondary),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(g.identifier,
                        style: AppType.subtitle.copyWith(color: p.textPrimary)),
                    Text(g.sipEndpoint,
                        style: AppType.mono.copyWith(color: p.textTertiary)),
                  ],
                ),
              ),
              statusBadgeFor(context, g.status.name),
              const SizedBox(width: AppSpacing.xs),
              AppButton(
                label: 'Verify',
                icon: Icons.wifi_tethering,
                variant: AppButtonVariant.secondary,
                size: AppButtonSize.small,
                loading: _verifying,
                onPressed: _verifying ? null : _verify,
              ),
              AppIconButton(
                icon: _expanded ? Icons.expand_less : Icons.expand_more,
                onPressed: () => setState(() => _expanded = !_expanded),
                semanticLabel:
                    _expanded ? 'Collapse details' : 'Expand details',
              ),
            ],
          ),
          if (health.isNotEmpty || g.lastHeartbeat != null) ...<Widget>[
            const SizedBox(height: AppSpacing.sm),
            Wrap(
              spacing: AppSpacing.md,
              runSpacing: AppSpacing.xxs,
              children: <Widget>[
                _MetaChip(
                    label: 'Registration',
                    value: (health['registration'] ?? '—').toString()),
                if (health['latency_ms'] != null)
                  _MetaChip(
                      label: 'Latency', value: '${health['latency_ms']} ms'),
                if (health['usable_lines'] != null)
                  _MetaChip(
                      label: 'Usable lines',
                      value: '${health['usable_lines']}'),
                if (health['active_channels'] != null)
                  _MetaChip(
                      label: 'Active channels',
                      value: '${health['active_channels']}'),
                _MetaChip(
                  label: 'Last checked',
                  value: g.lastHeartbeat == null
                      ? 'never'
                      : DateFormat('d MMM HH:mm').format(g.lastHeartbeat!),
                ),
              ],
            ),
          ],
          if (_error != null) ...<Widget>[
            const SizedBox(height: AppSpacing.sm),
            InlineError(error: _error!, onRetry: _verify),
          ],
          if (_probe != null) ...<Widget>[
            const SizedBox(height: AppSpacing.sm),
            InlineNotice(
              tone: _probe!.ok ? NoticeTone.success : NoticeTone.danger,
              message: _probe!.ok
                  ? '${_probe!.message}${_probe!.latencyMs != null ? ' (${_probe!.latencyMs} ms)' : ''}'
                  : 'Probe failed: ${_probe!.message}',
            ),
          ],
          if (_expanded) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            Divider(height: 1, color: p.outline),
            const SizedBox(height: AppSpacing.md),
            Row(
              children: <Widget>[
                Text('Lines',
                    style: AppType.bodyStrong.copyWith(color: p.textPrimary)),
                const Spacer(),
                AppButton(
                  label: 'Refresh lines',
                  variant: AppButtonVariant.ghost,
                  size: AppButtonSize.small,
                  loading: _loadingLines,
                  onPressed: _loadingLines ? null : _loadLines,
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.xs),
            if (_lines.isEmpty)
              Text(
                'No line detail yet. Run a verify probe to read SIM state from the gateway.',
                style: AppType.body.copyWith(color: p.textSecondary),
              )
            else
              AppTable(
                columns: const <AppTableColumn>[
                  AppTableColumn(label: 'Line', width: 150),
                  AppTableColumn(label: 'Number', width: 150),
                  AppTableColumn(label: 'State', width: 130),
                  AppTableColumn(label: 'Carrier', width: 140),
                  AppTableColumn(label: 'Signal', width: 90, numeric: true),
                  AppTableColumn(label: 'Channels', width: 100, numeric: true),
                  AppTableColumn(label: 'Usable', width: 100),
                ],
                rows: <TableRowData>[
                  for (final GatewayLine line in _lines)
                    TableRowData(
                      cells: <Widget>[
                        Text(line.lineId, style: AppType.mono),
                        Text(line.phoneNumber ?? '—', style: AppType.mono),
                        statusBadgeFor(context, line.state),
                        Text(line.carrier ?? '—', style: AppType.body),
                        Text(
                            line.signalPercent == null
                                ? '—'
                                : '${line.signalPercent}%',
                            style: AppType.mono),
                        Text('${line.activeChannels}', style: AppType.mono),
                        AppBadge(
                          label: line.usable ? 'Usable' : 'Not usable',
                          tone: line.usable
                              ? AppBadgeTone.success
                              : AppBadgeTone.danger,
                        ),
                      ],
                    ),
                ],
              ),
          ],
        ],
      ),
    );
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Text('$label: ',
            style: AppType.caption.copyWith(color: p.textTertiary)),
        Text(value,
            style: AppType.caption
                .copyWith(color: p.textSecondary, fontWeight: FontWeight.w600)),
      ],
    );
  }
}

class _RegisterGatewayDialog extends ConsumerStatefulWidget {
  const _RegisterGatewayDialog();

  @override
  ConsumerState<_RegisterGatewayDialog> createState() =>
      _RegisterGatewayDialogState();
}

class _RegisterGatewayDialogState
    extends ConsumerState<_RegisterGatewayDialog> {
  final TextEditingController _identifier = TextEditingController();
  final TextEditingController _endpoint =
      TextEditingController(text: 'sip:192.168.1.100:5060');
  bool _busy = false;
  Object? _error;

  @override
  void dispose() {
    _identifier.dispose();
    _endpoint.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_identifier.text.trim().isEmpty || _endpoint.text.trim().isEmpty) {
      setState(() => _error = 'Both fields are required.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(telephonyRepositoryProvider).registerGateway(
            _identifier.text.trim(),
            _endpoint.text.trim(),
          );
      ref.invalidate(gatewaysProvider);
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

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
              Text('Register a gateway',
                  style: AppType.subtitle.copyWith(color: p.textPrimary)),
              const SizedBox(height: AppSpacing.xxs),
              Text(
                'Registering does not connect anything. The gateway stays unverified until a probe succeeds.',
                style: AppType.body.copyWith(color: p.textSecondary),
              ),
              const SizedBox(height: AppSpacing.md),
              AppTextField(
                label: 'Identifier',
                controller: _identifier,
                hint: 'gw-sim-1',
                helper: 'A unique name within your workspace.',
              ),
              const SizedBox(height: AppSpacing.sm),
              AppTextField(
                label: 'SIP endpoint',
                controller: _endpoint,
                hint: 'sip:192.168.1.100:5060',
                prefixIcon: Icons.lan_outlined,
              ),
              if (_error != null) ...<Widget>[
                const SizedBox(height: AppSpacing.md),
                InlineError(error: _error!),
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
                    label: 'Register',
                    size: AppButtonSize.small,
                    loading: _busy,
                    onPressed: _busy ? null : _save,
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

class _SetupNote extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(Icons.terminal_outlined, size: 16, color: p.textSecondary),
              const SizedBox(width: AppSpacing.xs),
              Text('Expected SIP topology',
                  style: AppType.bodyStrong.copyWith(color: p.textPrimary)),
            ],
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            'SIM  →  GSM/VoLTE gateway  →  SIP  →  Asterisk (PJSIP)  →  ARI Stasis app  →  audio bridge',
            style: AppType.mono.copyWith(color: p.textSecondary),
          ),
        ],
      ),
    );
  }
}
