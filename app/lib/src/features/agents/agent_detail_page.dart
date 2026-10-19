import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../api/models.dart';
import '../../state/providers.dart';
import '../../theme/tokens.dart';
import '../../widgets/async_view.dart';
import '../../widgets/inputs.dart';
import '../../widgets/primitives.dart';
import '../../widgets/surfaces.dart';

class AgentDetailPage extends ConsumerStatefulWidget {
  const AgentDetailPage({super.key, required this.agentId});

  final String agentId;

  @override
  ConsumerState<AgentDetailPage> createState() => _AgentDetailPageState();
}

class _AgentDetailPageState extends ConsumerState<AgentDetailPage> {
  final TextEditingController _name = TextEditingController();
  final TextEditingController _greeting = TextEditingController();
  final TextEditingController _prompt = TextEditingController();
  final TextEditingController _transfer = TextEditingController();
  final TextEditingController _maxDuration = TextEditingController();
  AgentDirection _direction = AgentDirection.both;
  String _voice = 'Puck';
  bool _active = true;
  bool _loaded = false;
  bool _saving = false;
  Object? _saveError;
  String? _savedNote;

  @override
  void dispose() {
    _name.dispose();
    _greeting.dispose();
    _prompt.dispose();
    _transfer.dispose();
    _maxDuration.dispose();
    super.dispose();
  }

  void _hydrate(Agent a) {
    if (_loaded) return;
    _loaded = true;
    _name.text = a.name;
    _greeting.text = a.greeting;
    _prompt.text = a.systemPrompt;
    _transfer.text = a.humanTransferNumber ?? '';
    _maxDuration.text = a.maxDurationSeconds.toString();
    _direction = a.direction;
    _voice = a.voice;
    _active = a.isActive;
  }

  Future<void> _save() async {
    setState(() {
      _saving = true;
      _saveError = null;
      _savedNote = null;
    });
    try {
      await ref
          .read(agentRepositoryProvider)
          .update(widget.agentId, <String, dynamic>{
        'name': _name.text.trim(),
        'greeting': _greeting.text.trim(),
        'system_prompt': _prompt.text.trim(),
        'direction': _direction.name,
        'voice': _voice,
        'is_active': _active,
        'max_duration_seconds': int.tryParse(_maxDuration.text.trim()) ?? 600,
        'human_transfer_number':
            _transfer.text.trim().isEmpty ? null : _transfer.text.trim(),
      });
      ref.invalidate(agentsProvider);
      ref.invalidate(agentDetailProvider(widget.agentId));
      if (mounted) setState(() => _savedNote = 'Changes saved.');
    } catch (e) {
      if (mounted) setState(() => _saveError = e);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final AsyncValue<Map<String, dynamic>> detail =
        ref.watch(agentDetailProvider(widget.agentId));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            AppIconButton(
              icon: Icons.arrow_back,
              onPressed: () => context.go('/app/agents'),
              semanticLabel: 'Back to agents',
              tooltip: 'Back',
            ),
            const SizedBox(width: AppSpacing.xs),
            Text('Agents',
                style: AppType.body.copyWith(color: p.textSecondary)),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        AsyncView<Map<String, dynamic>>(
          value: detail,
          onRetry: () => ref.invalidate(agentDetailProvider(widget.agentId)),
          skeletonLines: 10,
          isEmpty: (Map<String, dynamic> _) => false,
          builder: (Map<String, dynamic> json) {
            final Agent agent = Agent.fromJson(json);
            _hydrate(agent);
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                PageHeader(
                  eyebrow: 'Agent',
                  title: agent.name,
                  description: agent.purpose,
                  actions: <Widget>[
                    AppBadge(
                      label: _active ? 'Active' : 'Disabled',
                      tone:
                          _active ? AppBadgeTone.success : AppBadgeTone.neutral,
                    ),
                    AppBadge(
                        label: 'v${agent.activeVersionNumber}',
                        tone: AppBadgeTone.neutral),
                  ],
                ),
                LayoutBuilder(
                  builder: (BuildContext context, BoxConstraints constraints) {
                    final bool stacked = constraints.maxWidth < 980;
                    final Widget editor = _EditorCard(
                      name: _name,
                      greeting: _greeting,
                      prompt: _prompt,
                      transfer: _transfer,
                      maxDuration: _maxDuration,
                      direction: _direction,
                      voice: _voice,
                      active: _active,
                      saving: _saving,
                      saveError: _saveError,
                      savedNote: _savedNote,
                      onDirection: (AgentDirection v) =>
                          setState(() => _direction = v),
                      onVoice: (String v) => setState(() => _voice = v),
                      onActive: (bool v) => setState(() => _active = v),
                      onSave: _save,
                    );
                    final Widget tester = _TestCard(agentId: widget.agentId);
                    if (stacked) {
                      return Column(
                        children: <Widget>[
                          editor,
                          const SizedBox(height: AppSpacing.lg),
                          tester,
                        ],
                      );
                    }
                    return Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Expanded(flex: 3, child: editor),
                        const SizedBox(width: AppSpacing.lg),
                        Expanded(flex: 2, child: tester),
                      ],
                    );
                  },
                ),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _EditorCard extends StatelessWidget {
  const _EditorCard({
    required this.name,
    required this.greeting,
    required this.prompt,
    required this.transfer,
    required this.maxDuration,
    required this.direction,
    required this.voice,
    required this.active,
    required this.saving,
    required this.saveError,
    required this.savedNote,
    required this.onDirection,
    required this.onVoice,
    required this.onActive,
    required this.onSave,
  });

  final TextEditingController name;
  final TextEditingController greeting;
  final TextEditingController prompt;
  final TextEditingController transfer;
  final TextEditingController maxDuration;
  final AgentDirection direction;
  final String voice;
  final bool active;
  final bool saving;
  final Object? saveError;
  final String? savedNote;
  final ValueChanged<AgentDirection> onDirection;
  final ValueChanged<String> onVoice;
  final ValueChanged<bool> onActive;
  final VoidCallback onSave;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return AppCard(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Configuration',
              style: AppType.subtitle.copyWith(color: p.textPrimary)),
          const SizedBox(height: AppSpacing.md),
          AppTextField(label: 'Name', controller: name),
          const SizedBox(height: AppSpacing.sm),
          AppTextField(label: 'Greeting', controller: greeting, maxLines: 2),
          const SizedBox(height: AppSpacing.sm),
          AppTextField(
            label: 'System prompt',
            controller: prompt,
            maxLines: 8,
            helper: 'Tone, boundaries and escalation rules.',
          ),
          const SizedBox(height: AppSpacing.sm),
          Row(
            children: <Widget>[
              Expanded(
                child: AppSelect<AgentDirection>(
                  label: 'Direction',
                  value: direction,
                  items: <DropdownMenuItem<AgentDirection>>[
                    for (final AgentDirection d in AgentDirection.values)
                      DropdownMenuItem<AgentDirection>(
                          value: d, child: Text(d.label)),
                  ],
                  onChanged: (AgentDirection? v) => onDirection(v ?? direction),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: AppSelect<String>(
                  label: 'Voice',
                  value: voice,
                  items: const <DropdownMenuItem<String>>[
                    DropdownMenuItem<String>(
                        value: 'Puck', child: Text('Puck')),
                    DropdownMenuItem<String>(
                        value: 'Charon', child: Text('Charon')),
                    DropdownMenuItem<String>(
                        value: 'Kore', child: Text('Kore')),
                    DropdownMenuItem<String>(
                        value: 'Fenrir', child: Text('Fenrir')),
                    DropdownMenuItem<String>(
                        value: 'Aoede', child: Text('Aoede')),
                  ],
                  onChanged: (String? v) => onVoice(v ?? voice),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Row(
            children: <Widget>[
              Expanded(
                child: AppTextField(
                  label: 'Human transfer number',
                  controller: transfer,
                  hint: '+1 555 0111',
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: AppTextField(
                  label: 'Max duration (seconds)',
                  controller: maxDuration,
                  keyboardType: TextInputType.number,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          AppSwitchRow(
            title: 'Agent active',
            description:
                'Disabled agents are skipped by inbound and outbound routing.',
            value: active,
            onChanged: onActive,
          ),
          if (saveError != null) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            InlineError(error: saveError!),
          ],
          if (savedNote != null) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            InlineNotice(tone: NoticeTone.success, message: savedNote!),
          ],
          const SizedBox(height: AppSpacing.md),
          Row(
            children: <Widget>[
              AppButton(
                  label: 'Save changes',
                  loading: saving,
                  onPressed: saving ? null : onSave),
            ],
          ),
        ],
      ),
    );
  }
}

class _TestCard extends ConsumerStatefulWidget {
  const _TestCard({required this.agentId});

  final String agentId;

  @override
  ConsumerState<_TestCard> createState() => _TestCardState();
}

class _TestCardState extends ConsumerState<_TestCard> {
  final TextEditingController _message =
      TextEditingController(text: 'What is your return policy?');
  bool _busy = false;
  Object? _error;
  Map<String, dynamic>? _response;

  @override
  void dispose() {
    _message.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return AppCard(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Test the agent',
              style: AppType.subtitle.copyWith(color: p.textPrimary)),
          const SizedBox(height: AppSpacing.xxs),
          Text(
            'Runs one turn against the configured prompt and knowledge bases. No call is placed.',
            style: AppType.body.copyWith(color: p.textSecondary),
          ),
          const SizedBox(height: AppSpacing.md),
          AppTextField(
              label: 'Caller message', controller: _message, maxLines: 3),
          const SizedBox(height: AppSpacing.md),
          AppButton(
            label: 'Send test message',
            icon: Icons.send_outlined,
            loading: _busy,
            expand: true,
            onPressed: _busy
                ? null
                : () async {
                    setState(() {
                      _busy = true;
                      _error = null;
                      _response = null;
                    });
                    try {
                      final Map<String, dynamic> r = await ref
                          .read(agentRepositoryProvider)
                          .test(widget.agentId, _message.text, <String>[]);
                      if (mounted) setState(() => _response = r);
                    } catch (e) {
                      if (mounted) setState(() => _error = e);
                    } finally {
                      if (mounted) setState(() => _busy = false);
                    }
                  },
          ),
          if (_error != null) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            InlineError(error: _error!),
          ],
          if (_response != null) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(AppSpacing.sm),
              decoration: BoxDecoration(
                  color: p.infoSurface, borderRadius: AppRadii.allSm),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('AGENT',
                      style: AppType.micro.copyWith(color: p.textTertiary)),
                  const SizedBox(height: AppSpacing.xxs),
                  Text(
                    _response!['response']?.toString() ??
                        _response!['message']?.toString() ??
                        'No response body.',
                    style: AppType.body.copyWith(color: p.textPrimary),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}
