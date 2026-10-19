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

/// Tamper-evident activity trail. Restricted to Owner and Admin server-side;
/// the UI states this rather than quietly returning nothing.
class AuditPage extends ConsumerStatefulWidget {
  const AuditPage({super.key});

  @override
  ConsumerState<AuditPage> createState() => _AuditPageState();
}

class _AuditPageState extends ConsumerState<AuditPage> {
  final TextEditingController _filter = TextEditingController();

  @override
  void initState() {
    super.initState();
    _filter.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _filter.dispose();
    super.dispose();
  }

  List<AuditEntry> _apply(List<AuditEntry> all) {
    final String q = _filter.text.trim().toLowerCase();
    if (q.isEmpty) return all;
    return all
        .where(
          (AuditEntry e) =>
              e.action.toLowerCase().contains(q) ||
              e.entityType.toLowerCase().contains(q) ||
              (e.entityId ?? '').toLowerCase().contains(q),
        )
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final AsyncValue<List<AuditEntry>> logs = ref.watch(auditLogsProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        PageHeader(
          eyebrow: 'Insights',
          title: 'Audit log',
          description:
              'Every privileged action is recorded with the acting user, entity and timestamp. Visible to Owners and Admins.',
          actions: <Widget>[
            AppButton(
              label: 'Refresh',
              icon: Icons.refresh,
              variant: AppButtonVariant.secondary,
              size: AppButtonSize.small,
              onPressed: () => ref.invalidate(auditLogsProvider),
            ),
          ],
        ),
        ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 360),
          child: AppTextField(
            label: 'Filter',
            controller: _filter,
            hint: 'campaign, agent, invited…',
            prefixIcon: Icons.search,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        AsyncView<List<AuditEntry>>(
          value: logs,
          onRetry: () => ref.invalidate(auditLogsProvider),
          skeletonLines: 8,
          isEmpty: (List<AuditEntry> list) => _apply(list).isEmpty,
          emptyTitle: _filter.text.trim().isEmpty
              ? 'No activity recorded'
              : 'No matching entries',
          emptyMessage: _filter.text.trim().isEmpty
              ? 'Audit entries appear as soon as someone changes a setting, starts a campaign or invites a teammate.'
              : 'No audit entry matches "${_filter.text}".',
          emptyIcon: Icons.receipt_long_outlined,
          builder: (List<AuditEntry> list) {
            final List<AuditEntry> rows = _apply(list);
            return AppTable(
              columns: const <AppTableColumn>[
                AppTableColumn(label: 'When', width: 160),
                AppTableColumn(label: 'Action', width: 200),
                AppTableColumn(label: 'Entity', width: 140),
                AppTableColumn(label: 'Entity ID', width: 190),
                AppTableColumn(label: 'Details', width: 320),
              ],
              rows: <TableRowData>[
                for (final AuditEntry e in rows)
                  TableRowData(
                    cells: <Widget>[
                      Text(
                        e.createdAt == null
                            ? '—'
                            : DateFormat('d MMM yyyy, HH:mm')
                                .format(e.createdAt!),
                        style: AppType.caption,
                      ),
                      Text(e.action,
                          style: AppType.mono.copyWith(color: p.textPrimary)),
                      Text(e.entityType, style: AppType.body),
                      Text(e.entityId ?? '—', style: AppType.mono),
                      Text(
                        _summarise(e.details),
                        style: AppType.caption.copyWith(color: p.textSecondary),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
              ],
            );
          },
        ),
      ],
    );
  }

  static String _summarise(Map<String, dynamic> details) {
    if (details.isEmpty) return '—';
    return details.entries
        .where((MapEntry<String, dynamic> e) => e.value != null)
        .take(4)
        .map((MapEntry<String, dynamic> e) => '${e.key}: ${e.value}')
        .join(' · ');
  }
}
