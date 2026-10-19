import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../api/models.dart';
import '../../state/providers.dart';
import '../../theme/tokens.dart';
import '../../widgets/async_view.dart';
import '../../widgets/inputs.dart';
import '../../widgets/primitives.dart';
import '../../widgets/surfaces.dart';

class CampaignsPage extends ConsumerWidget {
  const CampaignsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AppPalette p = context.palette;
    final AsyncValue<List<Campaign>> campaigns = ref.watch(campaignsProvider);
    final bool isAdmin = _isAdmin(ref);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        PageHeader(
          eyebrow: 'Outreach',
          title: 'Campaigns',
          description:
              'Paced outbound calling. Every dial keeps a recorded reason, and nothing starts without explicit approval.',
          actions: <Widget>[
            if (isAdmin)
              AppButton(
                label: 'New campaign',
                icon: Icons.add,
                size: AppButtonSize.small,
                onPressed: () => showDialog<void>(
                  context: context,
                  builder: (BuildContext context) =>
                      const _CreateCampaignDialog(),
                ),
              ),
          ],
        ),
        AsyncView<List<Campaign>>(
          value: campaigns,
          onRetry: () => ref.invalidate(campaignsProvider),
          skeletonLines: 5,
          isEmpty: (List<Campaign> list) => list.isEmpty,
          emptyTitle: 'No campaigns yet',
          emptyMessage:
              'Create a campaign, run a dry-run to check calling hours and suppression, then start it when you are ready.',
          emptyIcon: Icons.campaign_outlined,
          emptyAction: isAdmin
              ? AppButton(
                  label: 'Create a campaign',
                  size: AppButtonSize.small,
                  onPressed: () => showDialog<void>(
                    context: context,
                    builder: (BuildContext context) =>
                        const _CreateCampaignDialog(),
                  ),
                )
              : null,
          builder: (List<Campaign> list) => Column(
            children: <Widget>[
              for (final Campaign c in list)
                Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.md),
                  child: _CampaignCard(campaign: c, isAdmin: isAdmin),
                ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          'Calling windows, retry limits and concurrency are enforced server-side. A paused campaign stops '
          'dialling immediately; in-flight calls finish normally.',
          style: AppType.caption.copyWith(color: p.textTertiary),
        ),
      ],
    );
  }

  static bool _isAdmin(WidgetRef ref) {
    final String role = ref.watch(authProvider).session?.role ?? 'operator';
    return role == 'owner' || role == 'admin';
  }
}

class _CampaignCard extends ConsumerStatefulWidget {
  const _CampaignCard({required this.campaign, required this.isAdmin});

  final Campaign campaign;
  final bool isAdmin;

  @override
  ConsumerState<_CampaignCard> createState() => _CampaignCardState();
}

class _CampaignCardState extends ConsumerState<_CampaignCard> {
  bool _busy = false;
  Object? _error;
  ({bool ok, String message})? _result;
  Map<String, dynamic>? _dryRun;

  Future<void> _dryRunCheck() async {
    setState(() {
      _busy = true;
      _error = null;
      _result = null;
      _dryRun = null;
    });
    try {
      final Map<String, dynamic> r =
          await ref.read(campaignRepositoryProvider).dryRun(widget.campaign.id);
      if (mounted) setState(() => _dryRun = r);
    } catch (e) {
      if (mounted) setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _act({required bool start}) async {
    setState(() {
      _busy = true;
      _error = null;
      _result = null;
    });
    try {
      final Map<String, dynamic> r = start
          ? await ref.read(campaignRepositoryProvider).start(widget.campaign.id)
          : await ref
              .read(campaignRepositoryProvider)
              .pause(widget.campaign.id);
      ref.invalidate(campaignsProvider);
      if (mounted) {
        setState(() => _result = (
              ok: true,
              message: start
                  ? '${r['message'] ?? 'Campaign started.'} ${_sweepSummary(r)}.'
                  : r['message']?.toString() ?? 'Campaign updated.'
            ));
      }
    } catch (e) {
      if (mounted) setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// Runs one more dialer pass without changing the campaign's status.
  Future<void> _runSweep() async {
    setState(() {
      _busy = true;
      _error = null;
      _result = null;
    });
    try {
      final Map<String, dynamic> r =
          await ref.read(campaignRepositoryProvider).sweep(widget.campaign.id);
      ref.invalidate(campaignsProvider);
      if (mounted) {
        setState(() => _result = (ok: true, message: _sweepSummary(r)));
      }
    } catch (e) {
      if (mounted) setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// Reports what a dialer pass actually did, rather than implying success.
  static String _sweepSummary(Map<String, dynamic> r) {
    final int dialed = (r['dialed'] as num?)?.toInt() ?? 0;
    final int blocked = (r['blocked'] as num?)?.toInt() ?? 0;
    final int failed = (r['failed'] as num?)?.toInt() ?? 0;
    return '$dialed dialled · $blocked refused · $failed failed';
  }

  static String _dryRunMessage(Map<String, dynamic> r) {
    final int ready = (r['would_dial'] as num?)?.toInt() ?? 0;
    final int refused = (r['would_block'] as num?)?.toInt() ?? 0;
    final List<dynamic> warnings =
        (r['validation_warnings'] as List<dynamic>?) ?? const <dynamic>[];
    final StringBuffer buffer = StringBuffer(
        'Dry run: $ready ready to dial, $refused would be refused.');
    if (warnings.isNotEmpty) buffer.write(' ${warnings.join(' ')}');
    return buffer.toString();
  }

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final Campaign c = widget.campaign;
    final bool running = c.status == 'running';

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
                child: Icon(Icons.campaign_outlined,
                    size: 17, color: p.textSecondary),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(c.name,
                        style: AppType.subtitle.copyWith(color: p.textPrimary)),
                    Text(
                      'Window ${c.allowedStartHour}–${c.allowedEndHour} · '
                      'up to ${c.maxAttempts} attempts · concurrency ${c.concurrencyLimit}',
                      style: AppType.caption.copyWith(color: p.textTertiary),
                    ),
                  ],
                ),
              ),
              statusBadgeFor(context, c.status),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Wrap(
            spacing: AppSpacing.lg,
            runSpacing: AppSpacing.xs,
            children: <Widget>[
              _Stat(label: 'Contacts', value: '${c.totalContacts}'),
              _Stat(label: 'Successful', value: '${c.successfulCalls}'),
              _Stat(label: 'Failed', value: '${c.failedCalls}'),
              _Stat(
                label: 'Attempted',
                value: '${c.successfulCalls + c.failedCalls}',
              ),
            ],
          ),
          if (_dryRun != null) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            InlineNotice(
              tone: ((_dryRun!['would_dial'] as num?)?.toInt() ?? 0) > 0
                  ? NoticeTone.success
                  : NoticeTone.warning,
              message: _dryRunMessage(_dryRun!),
            ),
          ],
          if (_error != null) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            InlineError(error: _error!),
          ],
          if (_result != null) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            InlineNotice(tone: NoticeTone.success, message: _result!.message),
          ],
          if (widget.isAdmin) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            Row(
              children: <Widget>[
                AppButton(
                  label: 'Dry run',
                  icon: Icons.fact_check_outlined,
                  variant: AppButtonVariant.secondary,
                  size: AppButtonSize.small,
                  loading: _busy,
                  onPressed: _busy ? null : _dryRunCheck,
                ),
                const SizedBox(width: AppSpacing.xs),
                if (running)
                  AppButton(
                    label: 'Pause',
                    icon: Icons.pause_outlined,
                    size: AppButtonSize.small,
                    onPressed: _busy ? null : () => _act(start: false),
                  )
                else
                  AppButton(
                    label: 'Start',
                    icon: Icons.play_arrow_outlined,
                    size: AppButtonSize.small,
                    onPressed: _busy ? null : () => _act(start: true),
                  ),
                if (running) ...<Widget>[
                  const SizedBox(width: AppSpacing.xs),
                  AppButton(
                    label: 'Run dialer',
                    icon: Icons.sync_outlined,
                    variant: AppButtonVariant.secondary,
                    size: AppButtonSize.small,
                    onPressed: _busy ? null : _runSweep,
                  ),
                ],
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Text('$label ', style: AppType.caption.copyWith(color: p.textTertiary)),
        Text(value, style: AppType.bodyStrong.copyWith(color: p.textPrimary)),
      ],
    );
  }
}

class _CreateCampaignDialog extends ConsumerStatefulWidget {
  const _CreateCampaignDialog();

  @override
  ConsumerState<_CreateCampaignDialog> createState() =>
      _CreateCampaignDialogState();
}

class _CreateCampaignDialogState extends ConsumerState<_CreateCampaignDialog> {
  final TextEditingController _name = TextEditingController();
  final TextEditingController _start = TextEditingController(text: '09:00');
  final TextEditingController _end = TextEditingController(text: '20:00');
  final TextEditingController _zone = TextEditingController(text: 'UTC');
  String? _agentId;
  int _maxAttempts = 3;
  int _concurrency = 2;
  final Set<String> _selectedContacts = <String>{};
  bool _busy = false;
  Object? _error;

  @override
  void dispose() {
    _name.dispose();
    _start.dispose();
    _end.dispose();
    _zone.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_name.text.trim().isEmpty || _agentId == null) {
      setState(() => _error = 'A name and an agent are required.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(campaignRepositoryProvider).create(<String, dynamic>{
        'name': _name.text.trim(),
        'agent_id': _agentId,
        'allowed_start_hour': _start.text.trim(),
        'allowed_end_hour': _end.text.trim(),
        'timezone': _zone.text.trim(),
        'max_attempts': _maxAttempts,
        'concurrency_limit': _concurrency,
        'contact_ids': _selectedContacts.toList(),
      });
      ref.invalidate(campaignsProvider);
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
    final List<Agent> agents =
        ref.watch(agentsProvider).valueOrNull ?? <Agent>[];
    final List<Contact> contacts =
        ref.watch(contactsProvider).valueOrNull ?? <Contact>[];

    return Dialog(
      backgroundColor: p.surface,
      shape: const RoundedRectangleBorder(borderRadius: AppRadii.allMd),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 580, maxHeight: 640),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('New campaign',
                  style: AppType.subtitle.copyWith(color: p.textPrimary)),
              const SizedBox(height: AppSpacing.xxs),
              Text(
                'The campaign is created in Draft. Suppressed contacts are excluded automatically.',
                style: AppType.body.copyWith(color: p.textSecondary),
              ),
              const SizedBox(height: AppSpacing.md),
              Expanded(
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      AppTextField(
                          label: 'Name',
                          controller: _name,
                          hint: 'Renewal reminders'),
                      const SizedBox(height: AppSpacing.sm),
                      AppSelect<String?>(
                        label: 'Agent',
                        value: _agentId,
                        items: <DropdownMenuItem<String?>>[
                          const DropdownMenuItem<String?>(
                              value: null, child: Text('Select an agent')),
                          for (final Agent a in agents)
                            DropdownMenuItem<String?>(
                                value: a.id, child: Text(a.name)),
                        ],
                        onChanged: (String? v) => setState(() => _agentId = v),
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      Row(
                        children: <Widget>[
                          Expanded(
                            child: AppTextField(
                              label: 'Window start',
                              controller: _start,
                              hint: '09:00',
                              helper: '24-hour, local to the timezone.',
                            ),
                          ),
                          const SizedBox(width: AppSpacing.sm),
                          Expanded(
                              child: AppTextField(
                                  label: 'Window end',
                                  controller: _end,
                                  hint: '20:00')),
                        ],
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      Row(
                        children: <Widget>[
                          Expanded(
                              child: AppTextField(
                                  label: 'Timezone',
                                  controller: _zone,
                                  hint: 'UTC')),
                          const SizedBox(width: AppSpacing.sm),
                          Expanded(
                            child: AppSelect<int>(
                              label: 'Max attempts',
                              value: _maxAttempts,
                              items: const <DropdownMenuItem<int>>[
                                DropdownMenuItem<int>(
                                    value: 1, child: Text('1')),
                                DropdownMenuItem<int>(
                                    value: 2, child: Text('2')),
                                DropdownMenuItem<int>(
                                    value: 3, child: Text('3')),
                                DropdownMenuItem<int>(
                                    value: 4, child: Text('4')),
                                DropdownMenuItem<int>(
                                    value: 5, child: Text('5')),
                              ],
                              onChanged: (int? v) => setState(
                                  () => _maxAttempts = v ?? _maxAttempts),
                            ),
                          ),
                          const SizedBox(width: AppSpacing.sm),
                          Expanded(
                            child: AppSelect<int>(
                              label: 'Concurrency',
                              value: _concurrency,
                              items: const <DropdownMenuItem<int>>[
                                DropdownMenuItem<int>(
                                    value: 1, child: Text('1')),
                                DropdownMenuItem<int>(
                                    value: 2, child: Text('2')),
                                DropdownMenuItem<int>(
                                    value: 3, child: Text('3')),
                                DropdownMenuItem<int>(
                                    value: 5, child: Text('5')),
                              ],
                              onChanged: (int? v) => setState(
                                  () => _concurrency = v ?? _concurrency),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: AppSpacing.md),
                      Text(
                        'Contacts (${_selectedContacts.length} selected)',
                        style: AppType.label.copyWith(color: p.textSecondary),
                      ),
                      const SizedBox(height: AppSpacing.xxs),
                      if (contacts.isEmpty)
                        Text(
                          'No contacts yet. Add contacts before building a campaign.',
                          style:
                              AppType.caption.copyWith(color: p.textTertiary),
                        )
                      else
                        Container(
                          constraints: const BoxConstraints(maxHeight: 200),
                          decoration: BoxDecoration(
                            border: Border.all(color: p.outline),
                            borderRadius: AppRadii.allSm,
                          ),
                          child: ListView(
                            shrinkWrap: true,
                            children: <Widget>[
                              for (final Contact c in contacts)
                                CheckboxListTile(
                                  dense: true,
                                  value: _selectedContacts.contains(c.id),
                                  onChanged: c.isSuppressed
                                      ? null
                                      : (bool? v) => setState(() {
                                            if (v == true) {
                                              _selectedContacts.add(c.id);
                                            } else {
                                              _selectedContacts.remove(c.id);
                                            }
                                          }),
                                  title: Text(c.displayName,
                                      style: AppType.body
                                          .copyWith(color: p.textPrimary)),
                                  subtitle: Text(
                                    c.isSuppressed
                                        ? '${c.phoneNumber} · suppressed'
                                        : c.phoneNumber,
                                    style: AppType.caption.copyWith(
                                      color: c.isSuppressed
                                          ? p.danger
                                          : p.textTertiary,
                                    ),
                                  ),
                                  controlAffinity:
                                      ListTileControlAffinity.leading,
                                ),
                            ],
                          ),
                        ),
                      if (_error != null) ...<Widget>[
                        const SizedBox(height: AppSpacing.md),
                        InlineError(error: _error!),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: AppSpacing.md),
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
                    label: 'Create campaign',
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
