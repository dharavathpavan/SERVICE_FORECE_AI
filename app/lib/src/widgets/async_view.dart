import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_error.dart';
import '../theme/tokens.dart';
import 'surfaces.dart';

/// Renders a Riverpod [AsyncValue] with the four states every data view must have:
/// loading (skeleton), error (retry), empty (guidance) and data.
///
/// Using this everywhere removes ad-hoc spinners and raw exception strings.
class AsyncView<T> extends StatelessWidget {
  const AsyncView({
    super.key,
    required this.value,
    required this.builder,
    this.isEmpty,
    this.emptyTitle = 'Nothing here yet',
    this.emptyMessage = 'Data will appear here once it exists.',
    this.emptyIcon = Icons.inbox_outlined,
    this.emptyAction,
    this.onRetry,
    this.skeletonLines = 4,
    this.skeleton,
  });

  final AsyncValue<T> value;
  final Widget Function(T data) builder;
  final bool Function(T data)? isEmpty;
  final String emptyTitle;
  final String emptyMessage;
  final IconData emptyIcon;
  final Widget? emptyAction;
  final VoidCallback? onRetry;
  final int skeletonLines;
  final Widget? skeleton;

  @override
  Widget build(BuildContext context) {
    return value.when(
      loading: () => skeleton ?? _DefaultSkeleton(lines: skeletonLines),
      error: (Object error, StackTrace _) => AppErrorState(
        message: error is ApiError
            ? error.userMessage
            : 'Unexpected error. Please try again.',
        onRetry: error is ApiError && !error.retryable ? null : onRetry,
      ),
      data: (T data) {
        if (isEmpty?.call(data) ?? false) {
          return AppEmptyState(
            title: emptyTitle,
            message: emptyMessage,
            icon: emptyIcon,
            action: emptyAction,
          );
        }
        return builder(data);
      },
    );
  }
}

class _DefaultSkeleton extends StatelessWidget {
  const _DefaultSkeleton({required this.lines});

  final int lines;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const AppSkeleton(width: 180, height: 18),
          const SizedBox(height: AppSpacing.md),
          AppSkeleton(lines: lines),
        ],
      ),
    );
  }
}

/// Inline error banner for failures inside an otherwise-loaded screen.
class InlineError extends StatelessWidget {
  const InlineError({super.key, required this.error, this.onRetry});

  final Object error;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return AppErrorState(
      title: 'Action failed',
      message: error is ApiError
          ? (error as ApiError).userMessage
          : 'Unexpected error.',
      onRetry: onRetry,
    );
  }
}

/// Simple success/notice banner.
class InlineNotice extends StatelessWidget {
  const InlineNotice(
      {super.key, required this.message, this.tone = NoticeTone.info});

  final String message;
  final NoticeTone tone;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final (Color fg, Color bg, IconData icon) = switch (tone) {
      NoticeTone.info => (p.info, p.infoSurface, Icons.info_outline),
      NoticeTone.success => (
          p.success,
          p.successSurface,
          Icons.check_circle_outline
        ),
      NoticeTone.warning => (
          p.warning,
          p.warningSurface,
          Icons.warning_amber_outlined
        ),
      NoticeTone.danger => (p.danger, p.dangerSurface, Icons.error_outline),
    };
    return Container(
      padding: const EdgeInsets.all(AppSpacing.sm),
      decoration: BoxDecoration(color: bg, borderRadius: AppRadii.allSm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon, size: 16, color: fg),
          const SizedBox(width: AppSpacing.xs),
          Expanded(
              child: Text(message,
                  style: AppType.body.copyWith(color: p.textPrimary))),
        ],
      ),
    );
  }
}

enum NoticeTone { info, success, warning, danger }
