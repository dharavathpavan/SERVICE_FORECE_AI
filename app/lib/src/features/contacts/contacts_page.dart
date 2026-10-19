import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../api/models.dart';
import '../../state/providers.dart';
import '../../theme/tokens.dart';
import '../../widgets/async_view.dart';
import '../../widgets/inputs.dart';
import '../../widgets/primitives.dart';
import '../../widgets/surfaces.dart';

class ContactsPage extends ConsumerStatefulWidget {
  const ContactsPage({super.key});

  @override
  ConsumerState<ContactsPage> createState() => _ContactsPageState();
}

class _ContactsPageState extends ConsumerState<ContactsPage> {
  final TextEditingController _search = TextEditingController();
  bool _onlySuppressed = false;

  @override
  void initState() {
    super.initState();
    _search.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  List<Contact> _filter(List<Contact> all) {
    final String q = _search.text.trim().toLowerCase();
    return all.where((Contact c) {
      if (_onlySuppressed && !c.isSuppressed) return false;
      if (q.isEmpty) return true;
      return c.displayName.toLowerCase().contains(q) ||
          c.phoneNumber.toLowerCase().contains(q) ||
          (c.email ?? '').toLowerCase().contains(q);
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final AsyncValue<List<Contact>> contacts = ref.watch(contactsProvider);
    final bool isAdmin = _isAdmin(ref);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        PageHeader(
          eyebrow: 'Outreach',
          title: 'Contacts',
          description:
              'People and numbers you are permitted to call. Consent is recorded per contact and suppression is honoured.',
          actions: <Widget>[
            AppButton(
              label: 'Suppress a number',
              icon: Icons.block,
              variant: AppButtonVariant.secondary,
              size: AppButtonSize.small,
              onPressed: () => showDialog<void>(
                context: context,
                builder: (BuildContext context) => const _SuppressDialog(),
              ),
            ),
            if (isAdmin)
              AppButton(
                label: 'Add contact',
                icon: Icons.add,
                size: AppButtonSize.small,
                onPressed: () => showDialog<void>(
                  context: context,
                  builder: (BuildContext context) =>
                      const _CreateContactDialog(),
                ),
              ),
          ],
        ),
        Row(
          children: <Widget>[
            Expanded(
              child: AppTextField(
                label: 'Search',
                controller: _search,
                hint: 'Name, number or email',
                prefixIcon: Icons.search,
              ),
            ),
            const SizedBox(width: AppSpacing.md),
            Padding(
              padding: const EdgeInsets.only(top: AppSpacing.md),
              child: FilterChip(
                label: Text('Suppressed only',
                    style: AppType.label.copyWith(color: p.textSecondary)),
                selected: _onlySuppressed,
                onSelected: (bool v) => setState(() => _onlySuppressed = v),
                backgroundColor: p.surface,
                selectedColor: p.dangerSurface,
                side: BorderSide(color: _onlySuppressed ? p.danger : p.outline),
                checkmarkColor: p.danger,
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        AsyncView<List<Contact>>(
          value: contacts,
          onRetry: () => ref.invalidate(contactsProvider),
          skeletonLines: 6,
          isEmpty: (List<Contact> list) => _filter(list).isEmpty,
          emptyTitle: 'No contacts found',
          emptyMessage: _search.text.trim().isEmpty
              ? 'Add a contact, or import a list, to start calling.'
              : 'No contact matches "$_search". Try a different search.',
          emptyIcon: Icons.contacts_outlined,
          emptyAction: isAdmin
              ? AppButton(
                  label: 'Add contact',
                  size: AppButtonSize.small,
                  onPressed: () => showDialog<void>(
                    context: context,
                    builder: (BuildContext context) =>
                        const _CreateContactDialog(),
                  ),
                )
              : null,
          builder: (List<Contact> list) {
            final List<Contact> rows = _filter(list);
            return AppTable(
              columns: const <AppTableColumn>[
                AppTableColumn(label: 'Name', width: 200),
                AppTableColumn(label: 'Number', width: 160),
                AppTableColumn(label: 'Email', width: 220),
                AppTableColumn(label: 'Consent', width: 130),
                AppTableColumn(label: 'Status', width: 120),
                AppTableColumn(label: '', width: 60),
              ],
              rows: <TableRowData>[
                for (final Contact c in rows)
                  TableRowData(
                    cells: <Widget>[
                      Text(c.displayName,
                          style: AppType.body.copyWith(color: p.textPrimary)),
                      Text(c.phoneNumber, style: AppType.mono),
                      Text(c.email ?? '—', style: AppType.body),
                      AppBadge(
                        label: c.isSuppressed ? 'Suppressed' : 'Permitted',
                        tone: c.isSuppressed
                            ? AppBadgeTone.danger
                            : AppBadgeTone.success,
                      ),
                      Text(
                        c.isSuppressed ? 'Do not call' : 'Callable',
                        style: AppType.caption.copyWith(color: p.textSecondary),
                      ),
                      if (c.isSuppressed)
                        const SizedBox.shrink()
                      else
                        AppIconButton(
                          icon: Icons.block,
                          danger: true,
                          semanticLabel: 'Suppress ${c.phoneNumber}',
                          tooltip: 'Suppress',
                          onPressed: () => _suppress(context, ref, c),
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

  static bool _isAdmin(WidgetRef ref) {
    final String role = ref.watch(authProvider).session?.role ?? 'operator';
    return role == 'owner' || role == 'admin';
  }

  static Future<void> _suppress(
      BuildContext context, WidgetRef ref, Contact c) async {
    final bool? ok = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) => AlertDialog(
        title: const Text('Add to suppression list?'),
        content: Text(
          '${c.phoneNumber} will be excluded from all outbound calling. This does not remove the contact.',
        ),
        actions: <Widget>[
          TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel')),
          TextButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Suppress')),
        ],
      ),
    );
    if (ok != true) return;
    await ref.read(contactRepositoryProvider).suppress(c.phoneNumber);
    ref.invalidate(contactsProvider);
  }
}

class _CreateContactDialog extends ConsumerStatefulWidget {
  const _CreateContactDialog();

  @override
  ConsumerState<_CreateContactDialog> createState() =>
      _CreateContactDialogState();
}

class _CreateContactDialogState extends ConsumerState<_CreateContactDialog> {
  final TextEditingController _phone = TextEditingController();
  final TextEditingController _first = TextEditingController();
  final TextEditingController _last = TextEditingController();
  final TextEditingController _email = TextEditingController();
  String _source = 'web_form';
  bool _busy = false;
  Object? _error;

  @override
  void dispose() {
    _phone.dispose();
    _first.dispose();
    _last.dispose();
    _email.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_phone.text.trim().isEmpty) {
      setState(() => _error = 'A phone number is required.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(contactRepositoryProvider).create(<String, dynamic>{
        'phone_number': _phone.text.trim(),
        if (_first.text.trim().isNotEmpty) 'first_name': _first.text.trim(),
        if (_last.text.trim().isNotEmpty) 'last_name': _last.text.trim(),
        if (_email.text.trim().isNotEmpty) 'email': _email.text.trim(),
        'consent_source': _source,
      });
      ref.invalidate(contactsProvider);
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
              Text('Add contact',
                  style: AppType.subtitle.copyWith(color: p.textPrimary)),
              const SizedBox(height: AppSpacing.xxs),
              Text(
                'Adding a contact records lawful calling consent with the source you choose.',
                style: AppType.body.copyWith(color: p.textSecondary),
              ),
              const SizedBox(height: AppSpacing.md),
              AppTextField(
                label: 'Phone number',
                controller: _phone,
                hint: '+1 555 0100',
                prefixIcon: Icons.dialpad_outlined,
                keyboardType: TextInputType.phone,
              ),
              const SizedBox(height: AppSpacing.sm),
              Row(
                children: <Widget>[
                  Expanded(
                      child: AppTextField(
                          label: 'First name', controller: _first)),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                      child:
                          AppTextField(label: 'Last name', controller: _last)),
                ],
              ),
              const SizedBox(height: AppSpacing.sm),
              AppTextField(
                  label: 'Email (optional)',
                  controller: _email,
                  keyboardType: TextInputType.emailAddress),
              const SizedBox(height: AppSpacing.sm),
              AppSelect<String>(
                label: 'Consent source',
                value: _source,
                items: const <DropdownMenuItem<String>>[
                  DropdownMenuItem<String>(
                      value: 'web_form', child: Text('Web form')),
                  DropdownMenuItem<String>(
                      value: 'inbound_call', child: Text('Inbound call')),
                  DropdownMenuItem<String>(
                      value: 'verbal', child: Text('Verbal consent')),
                  DropdownMenuItem<String>(
                      value: 'csv_bulk_import', child: Text('Imported list')),
                ],
                onChanged: (String? v) =>
                    setState(() => _source = v ?? _source),
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
                    label: 'Add contact',
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

class _SuppressDialog extends ConsumerStatefulWidget {
  const _SuppressDialog();

  @override
  ConsumerState<_SuppressDialog> createState() => _SuppressDialogState();
}

class _SuppressDialogState extends ConsumerState<_SuppressDialog> {
  final TextEditingController _phone = TextEditingController();
  String _reason = 'caller_requested_opt_out';
  bool _busy = false;
  Object? _error;

  @override
  void dispose() {
    _phone.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_phone.text.trim().isEmpty) {
      setState(() => _error = 'Enter the number to suppress.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref
          .read(contactRepositoryProvider)
          .suppress(_phone.text.trim(), reason: _reason);
      ref.invalidate(contactsProvider);
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
        constraints: const BoxConstraints(maxWidth: 440),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Suppress a number',
                  style: AppType.subtitle.copyWith(color: p.textPrimary)),
              const SizedBox(height: AppSpacing.xxs),
              Text(
                'The number is added to the do-not-call registry and excluded from every outbound path, '
                'including campaigns.',
                style: AppType.body.copyWith(color: p.textSecondary),
              ),
              const SizedBox(height: AppSpacing.md),
              AppTextField(
                label: 'Phone number',
                controller: _phone,
                hint: '+1 555 0100',
                prefixIcon: Icons.dialpad_outlined,
              ),
              const SizedBox(height: AppSpacing.sm),
              AppSelect<String>(
                label: 'Reason',
                value: _reason,
                items: const <DropdownMenuItem<String>>[
                  DropdownMenuItem<String>(
                      value: 'caller_requested_opt_out',
                      child: Text('Caller asked to stop')),
                  DropdownMenuItem<String>(
                      value: 'wrong_number', child: Text('Wrong number')),
                  DropdownMenuItem<String>(
                      value: 'complaint', child: Text('Complaint received')),
                  DropdownMenuItem<String>(
                      value: 'regulatory', child: Text('Regulatory request')),
                ],
                onChanged: (String? v) =>
                    setState(() => _reason = v ?? _reason),
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
                    label: 'Suppress',
                    variant: AppButtonVariant.danger,
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
