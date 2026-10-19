import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../api/api_client.dart';
import '../../state/providers.dart';
import '../../theme/tokens.dart';
import '../../widgets/async_view.dart';
import '../../widgets/inputs.dart';
import '../../widgets/primitives.dart';
import '../../widgets/surfaces.dart';

/// Lightweight view of a membership row returned by `/organizations/members`.
class Membership {
  const Membership({
    required this.id,
    required this.userId,
    required this.role,
    required this.email,
    required this.fullName,
    required this.isActive,
    this.createdAt,
  });

  final String id;
  final String userId;
  final String role;
  final String email;
  final String fullName;
  final bool isActive;
  final DateTime? createdAt;

  factory Membership.fromJson(Map<String, dynamic> j) {
    final Map<String, dynamic> u = j.mapOr('user');
    return Membership(
      id: j.str('id'),
      userId: j.str('user_id'),
      role: j.str('role', fallback: 'operator'),
      email: u.str('email'),
      fullName: u.str('full_name', fallback: 'Unknown user'),
      isActive: u.boolOr('is_active', true),
      createdAt: j.dateOrNull('created_at'),
    );
  }

  String get initials {
    final List<String> parts = fullName.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty || parts.first.isEmpty) return 'U';
    if (parts.length == 1) return parts.first.substring(0, 1).toUpperCase();
    return (parts.first.substring(0, 1) + parts.last.substring(0, 1))
        .toUpperCase();
  }
}

const List<String> kRoles = <String>['owner', 'admin', 'operator', 'viewer'];

class TeamPage extends ConsumerWidget {
  const TeamPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AppPalette p = context.palette;
    final AsyncValue<List<Map<String, dynamic>>> members =
        ref.watch(teamMembersProvider);
    final String myRole = ref.watch(authProvider).session?.role ?? 'operator';
    final String? myUserId = ref.watch(authProvider).session?.user.id;
    final bool canManage = myRole == 'owner' || myRole == 'admin';
    final bool isOwner = myRole == 'owner';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        PageHeader(
          eyebrow: 'Administration',
          title: 'Team',
          description:
              'People with access to this workspace. Roles are enforced server-side, not just hidden in the interface.',
          actions: <Widget>[
            if (canManage)
              AppButton(
                label: 'Invite teammate',
                icon: Icons.person_add_alt,
                size: AppButtonSize.small,
                onPressed: () => showDialog<void>(
                  context: context,
                  builder: (BuildContext context) => const _InviteDialog(),
                ),
              ),
          ],
        ),
        AsyncView<List<Map<String, dynamic>>>(
          value: members,
          onRetry: () => ref.invalidate(teamMembersProvider),
          skeletonLines: 5,
          isEmpty: (List<Map<String, dynamic>> list) => list.isEmpty,
          emptyTitle: 'No team members found',
          emptyMessage: 'Invite a teammate to share this workspace.',
          emptyIcon: Icons.groups_outlined,
          builder: (List<Map<String, dynamic>> list) {
            final List<Membership> rows =
                list.map(Membership.fromJson).toList();
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                AppTable(
                  columns: <AppTableColumn>[
                    const AppTableColumn(label: 'Member', width: 260),
                    const AppTableColumn(label: 'Email', width: 240),
                    const AppTableColumn(label: 'Role', width: 170),
                    const AppTableColumn(label: 'Status', width: 110),
                    const AppTableColumn(label: 'Joined', width: 140),
                    AppTableColumn(label: '', width: canManage ? 120 : 0),
                  ],
                  rows: <TableRowData>[
                    for (final Membership m in rows)
                      TableRowData(
                        cells: <Widget>[
                          Row(
                            children: <Widget>[
                              CircleAvatar(
                                radius: 14,
                                backgroundColor: p.surfaceVariant,
                                child: Text(
                                  m.initials,
                                  style: AppType.micro
                                      .copyWith(color: p.textPrimary),
                                ),
                              ),
                              const SizedBox(width: AppSpacing.xs),
                              Flexible(
                                child: Text(
                                  m.userId == myUserId
                                      ? '${m.fullName} (you)'
                                      : m.fullName,
                                  style: AppType.bodyStrong
                                      .copyWith(color: p.textPrimary),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ],
                          ),
                          Text(m.email, style: AppType.body),
                          if (isOwner)
                            Container(
                              height: 34,
                              padding: const EdgeInsets.symmetric(
                                  horizontal: AppSpacing.xs),
                              decoration: BoxDecoration(
                                color: p.surface,
                                borderRadius: AppRadii.allSm,
                                border: Border.all(color: p.outline),
                              ),
                              child: DropdownButton<String>(
                                value: m.role,
                                isDense: true,
                                isExpanded: true,
                                underline: const SizedBox.shrink(),
                                dropdownColor: p.surface,
                                style:
                                    AppType.body.copyWith(color: p.textPrimary),
                                icon: Icon(Icons.expand_more,
                                    size: 16, color: p.textTertiary),
                                items: <DropdownMenuItem<String>>[
                                  for (final String r in kRoles)
                                    DropdownMenuItem<String>(
                                      value: r,
                                      child: Text(_roleLabel(r),
                                          style: AppType.body
                                              .copyWith(color: p.textPrimary)),
                                    ),
                                ],
                                onChanged: (String? v) {
                                  if (v == null || v == m.role) return;
                                  unawaited(_changeRole(ref, m, v));
                                },
                              ),
                            )
                          else
                            AppBadge(
                              label: _roleLabel(m.role),
                              tone: m.role == 'owner'
                                  ? AppBadgeTone.accent
                                  : AppBadgeTone.neutral,
                            ),
                          AppBadge(
                            label: m.isActive ? 'Active' : 'Disabled',
                            tone: m.isActive
                                ? AppBadgeTone.success
                                : AppBadgeTone.neutral,
                          ),
                          Text(
                            m.createdAt == null
                                ? '—'
                                : DateFormat('d MMM yyyy').format(m.createdAt!),
                            style: AppType.caption,
                          ),
                          if (canManage && m.userId != myUserId)
                            AppIconButton(
                              icon: Icons.person_remove_outlined,
                              danger: true,
                              semanticLabel: 'Remove ${m.fullName}',
                              tooltip: 'Remove',
                              onPressed: () => _confirmRemove(context, ref, m),
                            )
                          else
                            const SizedBox.shrink(),
                        ],
                      ),
                  ],
                ),
                const SizedBox(height: AppSpacing.md),
                Text(
                  isOwner
                      ? 'As Owner you can change any role. You cannot downgrade or remove your own Owner membership.'
                      : 'Only Owners can change roles. Admins can invite and remove other members.',
                  style: AppType.caption.copyWith(color: p.textTertiary),
                ),
              ],
            );
          },
        ),
      ],
    );
  }

  static String _roleLabel(String role) => switch (role) {
        'owner' => 'Owner',
        'admin' => 'Admin',
        'operator' => 'Operator',
        'viewer' => 'Viewer',
        _ => role,
      };

  /// Role changes are Owner-only server-side; a rejection simply leaves the row
  /// unchanged on the next refresh.
  static Future<void> _changeRole(
      WidgetRef ref, Membership m, String role) async {
    try {
      await ref.read(teamRepositoryProvider).updateRole(m.id, role);
    } catch (_) {
      // Owner-only on the server; the row renders unchanged until the refresh.
    } finally {
      ref.invalidate(teamMembersProvider);
    }
  }

  static Future<void> _confirmRemove(
      BuildContext context, WidgetRef ref, Membership m) async {
    final bool? ok = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) => AlertDialog(
        title: const Text('Remove team member?'),
        content: Text(
            '${m.fullName} will lose access to this workspace immediately.'),
        actions: <Widget>[
          TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel')),
          TextButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Remove')),
        ],
      ),
    );
    if (ok != true) return;
    await ref.read(teamRepositoryProvider).remove(m.id);
    ref.invalidate(teamMembersProvider);
  }
}

class _InviteDialog extends ConsumerStatefulWidget {
  const _InviteDialog();

  @override
  ConsumerState<_InviteDialog> createState() => _InviteDialogState();
}

class _InviteDialogState extends ConsumerState<_InviteDialog> {
  final TextEditingController _email = TextEditingController();
  String _role = 'operator';
  bool _busy = false;
  Object? _error;

  @override
  void dispose() {
    _email.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Dialog(
      backgroundColor: p.surface,
      shape: const RoundedRectangleBorder(borderRadius: AppRadii.allMd),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 440),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Invite a teammate',
                  style: AppType.subtitle.copyWith(color: p.textPrimary)),
              const SizedBox(height: AppSpacing.xxs),
              Text(
                'The invitation is valid for 7 days. Delivery depends on your configured mail provider.',
                style: AppType.body.copyWith(color: p.textSecondary),
              ),
              const SizedBox(height: AppSpacing.md),
              AppTextField(
                label: 'Email',
                controller: _email,
                hint: 'teammate@company.com',
                prefixIcon: Icons.mail_outline,
                keyboardType: TextInputType.emailAddress,
              ),
              const SizedBox(height: AppSpacing.sm),
              AppSelect<String>(
                label: 'Role',
                value: _role,
                items: <DropdownMenuItem<String>>[
                  for (final String r in kRoles)
                    DropdownMenuItem<String>(
                      value: r,
                      child: Text(r == 'owner'
                          ? 'Owner (full control)'
                          : '${r[0].toUpperCase()}${r.substring(1)}'),
                    ),
                ],
                onChanged: (String? v) => setState(() => _role = v ?? _role),
                helper: 'Choose the smallest role the person needs.',
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
                    label: 'Send invite',
                    size: AppButtonSize.small,
                    loading: _busy,
                    onPressed: _busy
                        ? null
                        : () async {
                            if (!_email.text.contains('@')) {
                              setState(() =>
                                  _error = 'Enter a valid email address.');
                              return;
                            }
                            setState(() {
                              _busy = true;
                              _error = null;
                            });
                            try {
                              await ref
                                  .read(teamRepositoryProvider)
                                  .invite(_email.text.trim(), _role);
                              ref.invalidate(teamMembersProvider);
                              if (context.mounted) Navigator.of(context).pop();
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
