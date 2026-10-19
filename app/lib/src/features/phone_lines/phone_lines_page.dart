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

class PhoneLinesPage extends ConsumerWidget {
  const PhoneLinesPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AppPalette p = context.palette;
    final AsyncValue<List<PhoneConnection>> lines =
        ref.watch(phoneConnectionsProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        PageHeader(
          eyebrow: 'Telephony',
          title: 'Phone lines',
          description:
              'Numbers your agents can answer or dial from. A line is unverified until a real probe confirms it.',
          actions: <Widget>[
            AppButton(
              label: 'Add line',
              icon: Icons.add,
              size: AppButtonSize.small,
              onPressed: () => showDialog<void>(
                context: context,
                builder: (BuildContext context) => const _AddLineDialog(),
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        AppCard(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Icon(Icons.help_outline, size: 16, color: p.accent),
                  const SizedBox(width: AppSpacing.xs),
                  Text('How to link a number',
                      style: AppType.bodyStrong.copyWith(color: p.textPrimary)),
                ],
              ),
              const SizedBox(height: AppSpacing.xs),
              Text(
                '1. Register the gateway that holds the SIM (Telephony → Gateways) and verify it. '
                '2. Add the number here and choose the direction it may be used for. '
                '3. Run "Verify line" — a number is never treated as connected just because it was typed in. '
                '4. Assign an agent, then dial it from Calls → Place call, or attach it to a campaign.',
                style: AppType.body.copyWith(color: p.textSecondary),
              ),
              const SizedBox(height: AppSpacing.xs),
              Text(
                'Consumer phones and USB modems cannot stream the full-duplex audio the AI needs, so real calls '
                'require a certified GSM/VoLTE gateway that terminates SIP. Without one, every screen still works '
                'against the built-in mock line.',
                style: AppType.caption.copyWith(color: p.textTertiary),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        AsyncView<List<PhoneConnection>>(
          value: lines,
          onRetry: () => ref.invalidate(phoneConnectionsProvider),
          skeletonLines: 5,
          isEmpty: (List<PhoneConnection> list) => list.isEmpty,
          emptyTitle: 'No phone lines yet',
          emptyMessage:
              'Add the number your SIM is attached to, then run a verification probe before using it for calls.',
          emptyIcon: Icons.phone_in_talk_outlined,
          emptyAction: AppButton(
            label: 'Add your first line',
            size: AppButtonSize.small,
            onPressed: () => showDialog<void>(
              context: context,
              builder: (BuildContext context) => const _AddLineDialog(),
            ),
          ),
          builder: (List<PhoneConnection> list) => Column(
            children: <Widget>[
              for (final PhoneConnection c in list)
                Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.md),
                  child: _LineCard(connection: c),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _LineCard extends ConsumerStatefulWidget {
  const _LineCard({required this.connection});

  final PhoneConnection connection;

  @override
  ConsumerState<_LineCard> createState() => _LineCardState();
}

class _LineCardState extends ConsumerState<_LineCard> {
  bool _verifying = false;
  ({bool verified, String status, String message})? _result;
  Object? _error;

  Future<void> _verify() async {
    setState(() {
      _verifying = true;
      _error = null;
      _result = null;
    });
    try {
      final ({bool verified, String status, String message}) r = await ref
          .read(telephonyRepositoryProvider)
          .verifyConnection(widget.connection.id);
      ref.invalidate(phoneConnectionsProvider);
      if (mounted) setState(() => _result = r);
    } catch (e) {
      if (mounted) setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _verifying = false);
    }
  }

  Future<void> _toggle({bool? inbound, bool? outbound}) async {
    try {
      await ref
          .read(telephonyRepositoryProvider)
          .updateConnection(widget.connection.id, <String, dynamic>{
        if (inbound != null) 'inbound_enabled': inbound,
        if (outbound != null) 'outbound_enabled': outbound,
      });
      ref.invalidate(phoneConnectionsProvider);
    } catch (e) {
      if (mounted) setState(() => _error = e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final PhoneConnection c = widget.connection;

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
                child: Icon(Icons.sim_card_outlined,
                    size: 17, color: p.textSecondary),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(c.friendlyName,
                        style: AppType.subtitle.copyWith(color: p.textPrimary)),
                    Text(c.phoneNumber,
                        style: AppType.mono.copyWith(color: p.textTertiary)),
                  ],
                ),
              ),
              AppBadge(
                label: c.isVerified ? 'Verified' : 'Unverified',
                tone:
                    c.isVerified ? AppBadgeTone.success : AppBadgeTone.warning,
                icon:
                    c.isVerified ? Icons.verified_outlined : Icons.help_outline,
              ),
              const SizedBox(width: AppSpacing.xs),
              statusBadgeFor(context, c.healthStatus),
              const SizedBox(width: AppSpacing.xs),
              AppButton(
                label: 'Verify line',
                icon: Icons.wifi_tethering,
                variant: AppButtonVariant.secondary,
                size: AppButtonSize.small,
                loading: _verifying,
                onPressed: _verifying ? null : _verify,
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Wrap(
            spacing: AppSpacing.lg,
            runSpacing: AppSpacing.xxs,
            children: <Widget>[
              _ToggleInline(
                label: 'Inbound',
                value: c.inboundEnabled,
                onChanged: (bool v) => _toggle(inbound: v),
              ),
              _ToggleInline(
                label: 'Outbound',
                value: c.outboundEnabled,
                onChanged: (bool v) => _toggle(outbound: v),
              ),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Text('Last checked: ',
                      style: AppType.caption.copyWith(color: p.textTertiary)),
                  Text(
                    c.lastHealthCheck == null
                        ? 'never'
                        : DateFormat('d MMM HH:mm').format(c.lastHealthCheck!),
                    style: AppType.caption.copyWith(
                        color: p.textSecondary, fontWeight: FontWeight.w600),
                  ),
                ],
              ),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Text('Type: ',
                      style: AppType.caption.copyWith(color: p.textTertiary)),
                  Text(c.connectionType,
                      style: AppType.caption.copyWith(
                          color: p.textSecondary, fontWeight: FontWeight.w600)),
                ],
              ),
            ],
          ),
          if (_error != null) ...<Widget>[
            const SizedBox(height: AppSpacing.sm),
            InlineError(error: _error!, onRetry: _verify),
          ],
          if (_result != null) ...<Widget>[
            const SizedBox(height: AppSpacing.sm),
            InlineNotice(
              tone: _result!.verified ? NoticeTone.success : NoticeTone.danger,
              message: _result!.verified
                  ? 'Line verified (${_result!.status}). ${_result!.message}'
                  : 'Not verified: ${_result!.message}',
            ),
          ],
        ],
      ),
    );
  }
}

class _ToggleInline extends StatelessWidget {
  const _ToggleInline(
      {required this.label, required this.value, required this.onChanged});

  final String label;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Text('$label ', style: AppType.caption.copyWith(color: p.textTertiary)),
        SizedBox(
          height: 22,
          child: Switch(
              value: value,
              onChanged: onChanged,
              materialTapTargetSize: MaterialTapTargetSize.shrinkWrap),
        ),
        Text(
          value ? 'on' : 'off',
          style: AppType.caption
              .copyWith(color: value ? p.success : p.textTertiary),
        ),
      ],
    );
  }
}

class _AddLineDialog extends ConsumerStatefulWidget {
  const _AddLineDialog();

  @override
  ConsumerState<_AddLineDialog> createState() => _AddLineDialogState();
}

class _AddLineDialogState extends ConsumerState<_AddLineDialog> {
  final TextEditingController _name = TextEditingController();
  final TextEditingController _number = TextEditingController();
  String _type = 'gsm_gateway';
  bool _busy = false;
  Object? _error;

  @override
  void dispose() {
    _name.dispose();
    _number.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_name.text.trim().isEmpty || _number.text.trim().isEmpty) {
      setState(() => _error = 'A name and number are required.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref
          .read(telephonyRepositoryProvider)
          .createConnection(<String, dynamic>{
        'friendly_name': _name.text.trim(),
        'phone_number': _number.text.trim(),
        'connection_type': _type,
      });
      ref.invalidate(phoneConnectionsProvider);
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
              Text('Add a phone line',
                  style: AppType.subtitle.copyWith(color: p.textPrimary)),
              const SizedBox(height: AppSpacing.xxs),
              Text(
                'The number starts unverified. Run a probe once the gateway is reachable.',
                style: AppType.body.copyWith(color: p.textSecondary),
              ),
              const SizedBox(height: AppSpacing.md),
              AppTextField(
                  label: 'Friendly name',
                  controller: _name,
                  hint: 'Support hotline'),
              const SizedBox(height: AppSpacing.sm),
              AppTextField(
                label: 'Phone number',
                controller: _number,
                hint: '+1 800 555 0100',
                prefixIcon: Icons.dialpad_outlined,
                keyboardType: TextInputType.phone,
              ),
              const SizedBox(height: AppSpacing.sm),
              AppSelect<String>(
                label: 'Connection type',
                value: _type,
                items: const <DropdownMenuItem<String>>[
                  DropdownMenuItem<String>(
                      value: 'gsm_gateway',
                      child: Text('GSM / VoLTE gateway (SIM)')),
                  DropdownMenuItem<String>(
                      value: 'sip_trunk', child: Text('SIP trunk')),
                  DropdownMenuItem<String>(
                      value: 'mock', child: Text('Mock (simulation)')),
                ],
                onChanged: (String? v) => setState(() => _type = v ?? _type),
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
                    label: 'Add line',
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
