import 'package:flutter/material.dart';

import '../theme/tokens.dart';
import 'primitives.dart';

/// Elevated container used for every content block.
class AppCard extends StatelessWidget {
  const AppCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(AppSpacing.md),
    this.onTap,
    this.selected = false,
    this.semanticLabel,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final VoidCallback? onTap;
  final bool selected;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final Widget content = Container(
      padding: padding,
      decoration: BoxDecoration(
        color: p.surface,
        borderRadius: AppRadii.allMd,
        border: Border.all(
            color: selected ? p.accent : p.outline, width: selected ? 1.5 : 1),
      ),
      child: child,
    );

    if (onTap == null) {
      return semanticLabel != null
          ? Semantics(label: semanticLabel, child: content)
          : content;
    }
    return Material(
      color: Colors.transparent,
      borderRadius: AppRadii.allMd,
      child: InkWell(
        onTap: onTap,
        borderRadius: AppRadii.allMd,
        hoverColor: p.surfaceVariant.withValues(alpha: 0.4),
        focusColor: p.focusRing.withValues(alpha: 0.25),
        child: content,
      ),
    );
  }
}

/// Page title with optional description and a right-aligned action area.
class PageHeader extends StatelessWidget {
  const PageHeader({
    super.key,
    required this.title,
    this.description,
    this.actions = const <Widget>[],
    this.eyebrow,
  });

  final String title;
  final String? description;
  final List<Widget> actions;
  final String? eyebrow;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.lg),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                if (eyebrow != null) ...<Widget>[
                  Text(eyebrow!.toUpperCase(),
                      style: AppType.micro.copyWith(color: p.textTertiary)),
                  const SizedBox(height: AppSpacing.xxs),
                ],
                Semantics(
                  header: true,
                  child: Text(title,
                      style: AppType.title.copyWith(color: p.textPrimary)),
                ),
                if (description != null) ...<Widget>[
                  const SizedBox(height: AppSpacing.xxs),
                  Text(
                    description!,
                    style: AppType.body.copyWith(color: p.textSecondary),
                  ),
                ],
              ],
            ),
          ),
          if (actions.isNotEmpty) ...<Widget>[
            const SizedBox(width: AppSpacing.md),
            Wrap(
                spacing: AppSpacing.xs,
                runSpacing: AppSpacing.xs,
                children: actions),
          ],
        ],
      ),
    );
  }
}

/// Small heading used to separate sections within a page.
class SectionHeader extends StatelessWidget {
  const SectionHeader(
      {super.key, required this.title, this.action, this.description});

  final String title;
  final Widget? action;
  final String? description;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: <Widget>[
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(title,
                    style: AppType.subtitle.copyWith(color: p.textPrimary)),
                if (description != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text(description!,
                        style:
                            AppType.caption.copyWith(color: p.textSecondary)),
                  ),
              ],
            ),
          ),
          if (action != null) action!,
        ],
      ),
    );
  }
}

/// Empty state. Always offers a next step, never a dead end.
class AppEmptyState extends StatelessWidget {
  const AppEmptyState({
    super.key,
    required this.title,
    required this.message,
    this.icon = Icons.inbox_outlined,
    this.action,
  });

  final String title;
  final String message;
  final IconData icon;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
          vertical: AppSpacing.xxl, horizontal: AppSpacing.lg),
      decoration: BoxDecoration(
        color: p.surface,
        borderRadius: AppRadii.allMd,
        border: Border.all(color: p.outline),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
                color: p.surfaceVariant, borderRadius: AppRadii.allMd),
            child: Icon(icon, size: 20, color: p.textTertiary),
          ),
          const SizedBox(height: AppSpacing.md),
          Text(title,
              style: AppType.subtitle.copyWith(color: p.textPrimary),
              textAlign: TextAlign.center),
          const SizedBox(height: AppSpacing.xxs),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Text(
              message,
              style: AppType.body.copyWith(color: p.textSecondary),
              textAlign: TextAlign.center,
            ),
          ),
          if (action != null) ...<Widget>[
            const SizedBox(height: AppSpacing.md),
            action!,
          ],
        ],
      ),
    );
  }
}

/// Error state with an explicit retry affordance and a readable reason.
class AppErrorState extends StatelessWidget {
  const AppErrorState(
      {super.key,
      required this.message,
      this.onRetry,
      this.title = 'Something went wrong'});

  final String message;
  final VoidCallback? onRetry;
  final String title;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        color: p.surface,
        borderRadius: AppRadii.allMd,
        border: Border.all(color: p.danger.withValues(alpha: 0.4)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(Icons.error_outline, size: 20, color: p.danger),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(title,
                    style: AppType.subtitle.copyWith(color: p.textPrimary)),
                const SizedBox(height: AppSpacing.xxs),
                Text(message,
                    style: AppType.body.copyWith(color: p.textSecondary)),
              ],
            ),
          ),
          if (onRetry != null)
            AppButton(
                label: 'Retry',
                icon: Icons.refresh,
                variant: AppButtonVariant.secondary,
                size: AppButtonSize.small,
                onPressed: onRetry),
        ],
      ),
    );
  }
}

/// Skeleton placeholder. Shown during loading instead of a bare spinner.
class AppSkeleton extends StatefulWidget {
  const AppSkeleton({
    super.key,
    this.lines = 3,
    this.height,
    this.width,
    this.radius = AppRadii.allSm,
  });

  final int lines;
  final double? height;
  final double? width;
  final BorderRadius radius;

  @override
  State<AppSkeleton> createState() => _AppSkeletonState();
}

class _AppSkeletonState extends State<AppSkeleton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1100),
  )..repeat(reverse: true);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final bool reduceMotion =
        MediaQuery.maybeOf(context)?.disableAnimations ?? false;

    Widget bar(double width, double height) => AnimatedBuilder(
          animation: _controller,
          builder: (BuildContext context, Widget? _) {
            final double t =
                reduceMotion ? 0.5 : 0.35 + (_controller.value * 0.35);
            return Container(
              width: width,
              height: height,
              decoration: BoxDecoration(
                color: Color.lerp(p.surfaceVariant, p.outline, t),
                borderRadius: widget.radius,
              ),
            );
          },
        );

    if (widget.height != null) {
      return bar(widget.width ?? double.infinity, widget.height!);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        for (int i = 0; i < widget.lines; i++) ...<Widget>[
          if (i > 0) const SizedBox(height: AppSpacing.sm),
          bar(
              i == widget.lines - 1
                  ? (widget.width ?? 240)
                  : (widget.width ?? double.infinity),
              14),
        ],
      ],
    );
  }
}

/// Data table shell: consistent header row, divider styling and horizontal scroll.
class AppTable extends StatelessWidget {
  const AppTable(
      {super.key,
      required this.columns,
      required this.rows,
      this.emptyMessage = 'No records'});

  final List<AppTableColumn> columns;
  final List<TableRowData> rows;
  final String emptyMessage;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Container(
      decoration: BoxDecoration(
        color: p.surface,
        borderRadius: AppRadii.allMd,
        border: Border.all(color: p.outline),
      ),
      clipBehavior: Clip.antiAlias,
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          return SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: ConstrainedBox(
              constraints: BoxConstraints(minWidth: constraints.maxWidth),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: <Widget>[
                  Container(
                    color: p.surfaceSunken,
                    padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.md, vertical: AppSpacing.sm),
                    child: Row(
                      children: <Widget>[
                        for (final AppTableColumn c in columns)
                          SizedBox(
                            width: c.width,
                            child: Text(
                              c.label.toUpperCase(),
                              style:
                                  AppType.micro.copyWith(color: p.textTertiary),
                            ),
                          ),
                      ],
                    ),
                  ),
                  if (rows.isEmpty)
                    Padding(
                      padding: const EdgeInsets.all(AppSpacing.lg),
                      child: Text(emptyMessage,
                          style: AppType.body.copyWith(color: p.textSecondary)),
                    )
                  else
                    for (int i = 0; i < rows.length; i++) ...<Widget>[
                      if (i > 0) Divider(height: 1, color: p.outline),
                      TableRowData.render(context, columns, rows[i]),
                    ],
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

class AppTableColumn {
  const AppTableColumn(
      {required this.label, required this.width, this.numeric = false});

  final String label;
  final double width;
  final bool numeric;
}

class TableRowData {
  const TableRowData({required this.cells, this.onTap});

  final List<Widget> cells;
  final VoidCallback? onTap;

  static Widget render(
      BuildContext context, List<AppTableColumn> columns, TableRowData row) {
    final AppPalette p = context.palette;
    final Widget content = Padding(
      padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md, vertical: AppSpacing.sm + 2),
      child: Row(
        children: <Widget>[
          for (int i = 0; i < columns.length; i++)
            SizedBox(
              width: columns[i].width,
              child: Align(
                alignment: columns[i].numeric
                    ? Alignment.centerRight
                    : Alignment.centerLeft,
                child: i < row.cells.length
                    ? row.cells[i]
                    : const SizedBox.shrink(),
              ),
            ),
        ],
      ),
    );
    if (row.onTap == null) return content;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: row.onTap,
        hoverColor: p.surfaceVariant.withValues(alpha: 0.4),
        focusColor: p.focusRing.withValues(alpha: 0.2),
        child: content,
      ),
    );
  }
}
