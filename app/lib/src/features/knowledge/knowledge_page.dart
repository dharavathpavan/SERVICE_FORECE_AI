import 'package:file_picker/file_picker.dart';
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

class KnowledgePage extends ConsumerStatefulWidget {
  const KnowledgePage({super.key});

  @override
  ConsumerState<KnowledgePage> createState() => _KnowledgePageState();
}

class _KnowledgePageState extends ConsumerState<KnowledgePage> {
  String? _selectedKbId;
  bool _uploading = false;
  Object? _uploadError;
  String? _uploadNote;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final AsyncValue<List<KnowledgeBase>> bases =
        ref.watch(knowledgeBasesProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        PageHeader(
          eyebrow: 'Knowledge',
          title: 'Knowledge bases',
          description:
              'Documents the agent can retrieve from. Uploads are chunked and embedded on the server.',
          actions: <Widget>[
            AppButton(
              label: 'New base',
              icon: Icons.add,
              size: AppButtonSize.small,
              onPressed: () => showDialog<void>(
                context: context,
                builder: (BuildContext context) => const _CreateBaseDialog(),
              ),
            ),
          ],
        ),
        AsyncView<List<KnowledgeBase>>(
          value: bases,
          onRetry: () => ref.invalidate(knowledgeBasesProvider),
          skeletonLines: 4,
          isEmpty: (List<KnowledgeBase> list) => list.isEmpty,
          emptyTitle: 'No knowledge bases',
          emptyMessage:
              'Create a base, then upload PDF, DOCX or text documents. Ingestion runs in the background.',
          emptyIcon: Icons.menu_book_outlined,
          emptyAction: AppButton(
            label: 'Create a base',
            size: AppButtonSize.small,
            onPressed: () => showDialog<void>(
              context: context,
              builder: (BuildContext context) => const _CreateBaseDialog(),
            ),
          ),
          builder: (List<KnowledgeBase> list) {
            _selectedKbId ??= list.first.id;
            final KnowledgeBase selected = list
                    .where((KnowledgeBase b) => b.id == _selectedKbId)
                    .firstOrNull ??
                list.first;
            _selectedKbId = selected.id;

            return LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                final bool stacked = constraints.maxWidth < 900;
                final Widget listPane = _BaseList(
                  bases: list,
                  selectedId: selected.id,
                  onSelect: (String id) => setState(() => _selectedKbId = id),
                );
                final Widget docsPane = _DocumentsPane(
                  key: ValueKey<String>(selected.id),
                  base: selected,
                  uploading: _uploading,
                  uploadError: _uploadError,
                  uploadNote: _uploadNote,
                  onPick: _pickAndUpload,
                );
                if (stacked) {
                  return Column(
                    children: <Widget>[
                      listPane,
                      const SizedBox(height: AppSpacing.md),
                      docsPane,
                    ],
                  );
                }
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    SizedBox(width: 280, child: listPane),
                    const SizedBox(width: AppSpacing.lg),
                    Expanded(child: docsPane),
                  ],
                );
              },
            );
          },
        ),
        const SizedBox(height: AppSpacing.md),
        Text(
          'Supported formats: PDF, DOCX, TXT and Markdown. Scanned PDFs without a text layer are not supported.',
          style: AppType.caption.copyWith(color: p.textTertiary),
        ),
      ],
    );
  }

  Future<void> _pickAndUpload(String kbId) async {
    setState(() {
      _uploading = true;
      _uploadError = null;
      _uploadNote = null;
    });
    try {
      final FilePickerResult? result = await FilePicker.platform.pickFiles(
        withData: true,
        type: FileType.custom,
        allowedExtensions: <String>['pdf', 'docx', 'txt', 'md'],
      );
      if (result == null || result.files.isEmpty) {
        setState(() => _uploading = false);
        return;
      }
      final PlatformFile file = result.files.first;
      final List<int>? bytes = file.bytes;
      if (bytes == null) {
        throw StateError('The selected file could not be read in the browser.');
      }
      await ref
          .read(knowledgeRepositoryProvider)
          .upload(kbId, file.name, bytes);
      ref.invalidate(documentsProvider(kbId));
      if (mounted) {
        setState(
          () => _uploadNote =
              '${file.name} uploaded. Ingestion will start shortly.',
        );
      }
    } catch (e) {
      if (mounted) setState(() => _uploadError = e);
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }
}

class _BaseList extends StatelessWidget {
  const _BaseList(
      {required this.bases, required this.selectedId, required this.onSelect});

  final List<KnowledgeBase> bases;
  final String selectedId;
  final ValueChanged<String> onSelect;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return AppCard(
      padding: const EdgeInsets.all(AppSpacing.xs),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          for (final KnowledgeBase b in bases)
            Material(
              color: b.id == selectedId ? p.infoSurface : Colors.transparent,
              borderRadius: AppRadii.allSm,
              child: InkWell(
                onTap: () => onSelect(b.id),
                borderRadius: AppRadii.allSm,
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.sm, vertical: AppSpacing.sm),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        b.name,
                        style: AppType.body.copyWith(
                          color: b.id == selectedId ? p.accent : p.textPrimary,
                          fontWeight: b.id == selectedId
                              ? FontWeight.w600
                              : FontWeight.w400,
                        ),
                      ),
                      if (b.description != null && b.description!.isNotEmpty)
                        Text(
                          b.description!,
                          style:
                              AppType.caption.copyWith(color: p.textTertiary),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _DocumentsPane extends ConsumerWidget {
  const _DocumentsPane({
    super.key,
    required this.base,
    required this.uploading,
    required this.uploadError,
    required this.uploadNote,
    required this.onPick,
  });

  final KnowledgeBase base;
  final bool uploading;
  final Object? uploadError;
  final String? uploadNote;
  final Future<void> Function(String kbId) onPick;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AppPalette p = context.palette;
    final AsyncValue<List<KnowledgeDocument>> docs =
        ref.watch(documentsProvider(base.id));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(base.name,
                      style: AppType.subtitle.copyWith(color: p.textPrimary)),
                  Text(
                    base.createdAt == null
                        ? 'Documents in this base'
                        : 'Created ${DateFormat('d MMM yyyy').format(base.createdAt!)}',
                    style: AppType.caption.copyWith(color: p.textTertiary),
                  ),
                ],
              ),
            ),
            AppButton(
              label: 'Upload document',
              icon: Icons.upload_file_outlined,
              variant: AppButtonVariant.secondary,
              size: AppButtonSize.small,
              loading: uploading,
              onPressed: uploading ? null : () => onPick(base.id),
            ),
          ],
        ),
        if (uploadError != null) ...<Widget>[
          const SizedBox(height: AppSpacing.sm),
          InlineError(error: uploadError!),
        ],
        if (uploadNote != null) ...<Widget>[
          const SizedBox(height: AppSpacing.sm),
          InlineNotice(tone: NoticeTone.success, message: uploadNote!),
        ],
        const SizedBox(height: AppSpacing.md),
        AsyncView<List<KnowledgeDocument>>(
          value: docs,
          onRetry: () => ref.invalidate(documentsProvider(base.id)),
          skeletonLines: 4,
          isEmpty: (List<KnowledgeDocument> list) => list.isEmpty,
          emptyTitle: 'No documents in this base',
          emptyMessage:
              'Upload a policy, FAQ or product guide so the agent can quote it accurately.',
          emptyIcon: Icons.description_outlined,
          emptyAction: AppButton(
            label: 'Upload document',
            size: AppButtonSize.small,
            onPressed: () => onPick(base.id),
          ),
          builder: (List<KnowledgeDocument> list) => AppTable(
            columns: const <AppTableColumn>[
              AppTableColumn(label: 'Document', width: 260),
              AppTableColumn(label: 'Type', width: 90),
              AppTableColumn(label: 'Status', width: 130),
              AppTableColumn(label: 'Chunks', width: 90, numeric: true),
              AppTableColumn(label: 'Added', width: 140),
              AppTableColumn(label: '', width: 60),
            ],
            rows: <TableRowData>[
              for (final KnowledgeDocument d in list)
                TableRowData(
                  cells: <Widget>[
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: <Widget>[
                        Text(d.title,
                            style: AppType.body.copyWith(color: p.textPrimary)),
                        if (d.errorMessage != null)
                          Text(
                            d.errorMessage!,
                            style: AppType.caption.copyWith(color: p.danger),
                            overflow: TextOverflow.ellipsis,
                          ),
                      ],
                    ),
                    Text(d.fileType.toUpperCase(),
                        style: AppType.micro.copyWith(color: p.textSecondary)),
                    statusBadgeFor(context, d.status),
                    Text('${d.chunkCount}', style: AppType.mono),
                    Text(
                      d.createdAt == null
                          ? '—'
                          : DateFormat('d MMM, HH:mm').format(d.createdAt!),
                      style: AppType.caption,
                    ),
                    AppIconButton(
                      icon: Icons.delete_outline,
                      danger: true,
                      semanticLabel: 'Delete ${d.title}',
                      tooltip: 'Delete',
                      onPressed: () async {
                        await ref
                            .read(knowledgeRepositoryProvider)
                            .deleteDocument(d.id);
                        ref.invalidate(documentsProvider(base.id));
                      },
                    ),
                  ],
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _CreateBaseDialog extends ConsumerStatefulWidget {
  const _CreateBaseDialog();

  @override
  ConsumerState<_CreateBaseDialog> createState() => _CreateBaseDialogState();
}

class _CreateBaseDialogState extends ConsumerState<_CreateBaseDialog> {
  final TextEditingController _name = TextEditingController();
  final TextEditingController _description = TextEditingController();
  bool _busy = false;
  Object? _error;

  @override
  void dispose() {
    _name.dispose();
    _description.dispose();
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
              Text('New knowledge base',
                  style: AppType.subtitle.copyWith(color: p.textPrimary)),
              const SizedBox(height: AppSpacing.md),
              AppTextField(
                  label: 'Name', controller: _name, hint: 'Product FAQs'),
              const SizedBox(height: AppSpacing.sm),
              AppTextField(
                  label: 'Description (optional)',
                  controller: _description,
                  maxLines: 3),
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
                    label: 'Create',
                    size: AppButtonSize.small,
                    loading: _busy,
                    onPressed: _busy
                        ? null
                        : () async {
                            if (_name.text.trim().isEmpty) {
                              setState(() => _error = 'A name is required.');
                              return;
                            }
                            setState(() {
                              _busy = true;
                              _error = null;
                            });
                            try {
                              await ref
                                  .read(knowledgeRepositoryProvider)
                                  .createBase(
                                    _name.text.trim(),
                                    _description.text.trim(),
                                  );
                              ref.invalidate(knowledgeBasesProvider);
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
