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

class AgentsPage extends ConsumerWidget {
  const AgentsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<List<Agent>> agents = ref.watch(agentsProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        PageHeader(
          eyebrow: 'Agents',
          title: 'AI agents',
          description:
              'Each agent has its own prompt, voice, direction and fallback behaviour.',
          actions: <Widget>[
            AppButton(
              label: 'New agent',
              icon: Icons.add,
              size: AppButtonSize.small,
              onPressed: () => _showCreateDialog(context, ref),
            ),
          ],
        ),
        AsyncView<List<Agent>>(
          value: agents,
          onRetry: () => ref.invalidate(agentsProvider),
          skeletonLines: 5,
          isEmpty: (List<Agent> list) => list.isEmpty,
          emptyTitle: 'No agents yet',
          emptyMessage:
              'Create an agent to answer calls. You can start with the mock voice provider and connect hardware later.',
          emptyIcon: Icons.smart_toy_outlined,
          emptyAction: AppButton(
            label: 'Create your first agent',
            size: AppButtonSize.small,
            onPressed: () => _showCreateDialog(context, ref),
          ),
          builder: (List<Agent> list) => AppTable(
            columns: const <AppTableColumn>[
              AppTableColumn(label: 'Name', width: 200),
              AppTableColumn(label: 'Purpose', width: 170),
              AppTableColumn(label: 'Direction', width: 130),
              AppTableColumn(label: 'Language', width: 110),
              AppTableColumn(label: 'Voice', width: 110),
              AppTableColumn(label: 'Status', width: 100),
            ],
            rows: <TableRowData>[
              for (final Agent a in list)
                TableRowData(
                  onTap: () => context.go('/app/agents/${a.id}'),
                  cells: <Widget>[
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: <Widget>[
                        Text(a.name,
                            style: AppType.bodyStrong
                                .copyWith(color: context.palette.textPrimary)),
                        if (a.description != null && a.description!.isNotEmpty)
                          Text(
                            a.description!,
                            style: AppType.caption
                                .copyWith(color: context.palette.textTertiary),
                            overflow: TextOverflow.ellipsis,
                          ),
                      ],
                    ),
                    Text(a.purpose, style: AppType.body),
                    Text(a.direction.label, style: AppType.body),
                    Text(a.language, style: AppType.mono),
                    Text(a.voice, style: AppType.body),
                    AppBadge(
                      label: a.isActive ? 'Active' : 'Disabled',
                      tone: a.isActive
                          ? AppBadgeTone.success
                          : AppBadgeTone.neutral,
                    ),
                  ],
                ),
            ],
          ),
        ),
      ],
    );
  }

  static Future<void> _showCreateDialog(
      BuildContext context, WidgetRef ref) async {
    await showDialog<void>(
      context: context,
      builder: (BuildContext context) => const _CreateAgentDialog(),
    );
  }
}

class _CreateAgentDialog extends ConsumerStatefulWidget {
  const _CreateAgentDialog();

  @override
  ConsumerState<_CreateAgentDialog> createState() => _CreateAgentDialogState();
}

class _CreateAgentDialogState extends ConsumerState<_CreateAgentDialog> {
  final TextEditingController _name = TextEditingController();
  final TextEditingController _greeting =
      TextEditingController(text: 'Hello, thanks for calling. How can I help?');
  final TextEditingController _prompt = TextEditingController(
    text:
        'You are a helpful customer support agent. Keep answers short, confirm details, '
        'and offer a human transfer when the caller asks.',
  );
  final TextEditingController _transfer = TextEditingController();
  AgentDirection _direction = AgentDirection.both;
  String _voice = 'Puck';
  bool _busy = false;
  Object? _error;

  @override
  void dispose() {
    _name.dispose();
    _greeting.dispose();
    _prompt.dispose();
    _transfer.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_name.text.trim().isEmpty) {
      setState(() => _error = 'Give the agent a name.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final Agent created =
          await ref.read(agentRepositoryProvider).create(<String, dynamic>{
        'name': _name.text.trim(),
        'greeting': _greeting.text.trim(),
        'system_prompt': _prompt.text.trim(),
        'direction': _direction.name,
        'voice': _voice,
        'language': 'en-US',
        'purpose': 'Customer support',
        if (_transfer.text.trim().isNotEmpty)
          'human_transfer_number': _transfer.text.trim(),
      });
      ref.invalidate(agentsProvider);
      if (mounted) {
        Navigator.of(context).pop();
        context.go('/app/agents/${created.id}');
      }
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
        constraints: const BoxConstraints(maxWidth: 540),
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('New agent',
                    style: AppType.subtitle.copyWith(color: p.textPrimary)),
                const SizedBox(height: AppSpacing.xxs),
                Text(
                  'You can refine every field afterwards. The agent starts active.',
                  style: AppType.body.copyWith(color: p.textSecondary),
                ),
                const SizedBox(height: AppSpacing.md),
                AppTextField(
                    label: 'Name', controller: _name, hint: 'Support agent'),
                const SizedBox(height: AppSpacing.sm),
                AppTextField(
                    label: 'Greeting', controller: _greeting, maxLines: 2),
                const SizedBox(height: AppSpacing.sm),
                AppTextField(
                  label: 'System prompt',
                  controller: _prompt,
                  maxLines: 5,
                  helper:
                      'Describe tone, boundaries and what the agent should do when unsure.',
                ),
                const SizedBox(height: AppSpacing.sm),
                Row(
                  children: <Widget>[
                    Expanded(
                      child: AppSelect<AgentDirection>(
                        label: 'Direction',
                        value: _direction,
                        items: <DropdownMenuItem<AgentDirection>>[
                          for (final AgentDirection d in AgentDirection.values)
                            DropdownMenuItem<AgentDirection>(
                                value: d, child: Text(d.label)),
                        ],
                        onChanged: (AgentDirection? v) =>
                            setState(() => _direction = v ?? _direction),
                      ),
                    ),
                    const SizedBox(width: AppSpacing.sm),
                    Expanded(
                      child: AppSelect<String>(
                        label: 'Voice',
                        value: _voice,
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
                        onChanged: (String? v) =>
                            setState(() => _voice = v ?? _voice),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.sm),
                AppTextField(
                  label: 'Human transfer number (optional)',
                  controller: _transfer,
                  hint: '+1 555 0111',
                  prefixIcon: Icons.support_agent_outlined,
                  helper:
                      'Used when the caller asks for a person and the agent is unavailable.',
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
                      label: 'Create agent',
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
      ),
    );
  }
}
