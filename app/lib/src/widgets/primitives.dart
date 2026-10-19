import 'package:flutter/material.dart';

import '../theme/tokens.dart';

/// Button variants. A single widget keeps hit-targets, focus and disabled states
/// consistent everywhere.
enum AppButtonVariant { primary, secondary, ghost, danger }

enum AppButtonSize { small, medium }

class AppButton extends StatelessWidget {
  const AppButton({
    super.key,
    required this.label,
    this.onPressed,
    this.variant = AppButtonVariant.primary,
    this.size = AppButtonSize.medium,
    this.icon,
    this.trailingIcon,
    this.loading = false,
    this.expand = false,
    this.tooltip,
  });

  final String label;
  final VoidCallback? onPressed;
  final AppButtonVariant variant;
  final AppButtonSize size;
  final IconData? icon;
  final IconData? trailingIcon;
  final bool loading;
  final bool expand;
  final String? tooltip;

  bool get _disabled => onPressed == null || loading;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final bool small = size == AppButtonSize.small;
    final double height = small ? 34 : 40;

    final (Color bg, Color fg, Color? border) = switch (variant) {
      AppButtonVariant.primary => (
          _disabled ? p.surfaceVariant : p.accent,
          _disabled ? p.textTertiary : p.onAccent,
          null,
        ),
      AppButtonVariant.secondary => (p.surface, p.textPrimary, p.outline),
      AppButtonVariant.ghost => (Colors.transparent, p.textSecondary, null),
      AppButtonVariant.danger => (
          _disabled ? p.surfaceVariant : p.danger,
          _disabled ? p.textTertiary : Colors.white,
          null,
        ),
    };

    final Widget content = Row(
      mainAxisSize: expand ? MainAxisSize.max : MainAxisSize.min,
      mainAxisAlignment: MainAxisAlignment.center,
      children: <Widget>[
        if (loading)
          SizedBox(
            width: 14,
            height: 14,
            child: CircularProgressIndicator(strokeWidth: 2, color: fg),
          )
        else if (icon != null)
          Icon(icon, size: small ? 15 : 16, color: fg),
        if (loading || icon != null) const SizedBox(width: AppSpacing.xs),
        Flexible(
          child: Text(
            label,
            overflow: TextOverflow.ellipsis,
            style: (small ? AppType.label : AppType.bodyStrong)
                .copyWith(color: fg),
          ),
        ),
        if (trailingIcon != null) ...<Widget>[
          const SizedBox(width: AppSpacing.xs),
          Icon(trailingIcon, size: small ? 15 : 16, color: fg),
        ],
      ],
    );

    final Widget button = Material(
      color: bg,
      borderRadius: AppRadii.allSm,
      child: InkWell(
        onTap: _disabled ? null : onPressed,
        borderRadius: AppRadii.allSm,
        hoverColor: variant == AppButtonVariant.primary
            ? p.accentHover
            : p.surfaceVariant.withValues(alpha: 0.7),
        focusColor: p.focusRing.withValues(alpha: 0.3),
        child: AnimatedContainer(
          duration: AppDurations.fast,
          height: height,
          padding: EdgeInsets.symmetric(
              horizontal: small ? AppSpacing.sm : AppSpacing.md),
          decoration: BoxDecoration(
            borderRadius: AppRadii.allSm,
            border: border != null ? Border.all(color: border) : null,
          ),
          alignment: Alignment.center,
          child: content,
        ),
      ),
    );

    final Widget sized =
        expand ? SizedBox(width: double.infinity, child: button) : button;
    return tooltip != null ? Tooltip(message: tooltip!, child: sized) : sized;
  }
}

/// Squared, subtle icon button used in toolbars and table rows.
class AppIconButton extends StatelessWidget {
  const AppIconButton({
    super.key,
    required this.icon,
    required this.onPressed,
    required this.semanticLabel,
    this.tooltip,
    this.danger = false,
  });

  final IconData icon;
  final VoidCallback? onPressed;
  final String semanticLabel;
  final String? tooltip;
  final bool danger;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final Widget b = Semantics(
      button: true,
      label: semanticLabel,
      child: Material(
        color: Colors.transparent,
        borderRadius: AppRadii.allSm,
        child: InkWell(
          onTap: onPressed,
          borderRadius: AppRadii.allSm,
          hoverColor: p.surfaceVariant,
          focusColor: p.focusRing.withValues(alpha: 0.3),
          child: SizedBox(
            width: 32,
            height: 32,
            child: Icon(icon,
                size: 16, color: danger ? p.danger : p.textSecondary),
          ),
        ),
      ),
    );
    return tooltip != null ? Tooltip(message: tooltip!, child: b) : b;
  }
}

enum AppBadgeTone { neutral, success, warning, danger, info, accent }

/// Compact status token. Used instead of raw coloured text.
class AppBadge extends StatelessWidget {
  const AppBadge(
      {super.key,
      required this.label,
      this.tone = AppBadgeTone.neutral,
      this.icon});

  final String label;
  final AppBadgeTone tone;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final (Color fg, Color bg) = switch (tone) {
      AppBadgeTone.neutral => (p.textSecondary, p.surfaceVariant),
      AppBadgeTone.success => (p.success, p.successSurface),
      AppBadgeTone.warning => (p.warning, p.warningSurface),
      AppBadgeTone.danger => (p.danger, p.dangerSurface),
      AppBadgeTone.info => (p.info, p.infoSurface),
      AppBadgeTone.accent => (p.accent, p.infoSurface),
    };

    return Container(
      padding:
          const EdgeInsets.symmetric(horizontal: AppSpacing.xs, vertical: 3),
      decoration: BoxDecoration(color: bg, borderRadius: AppRadii.allSm),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          if (icon != null) ...<Widget>[
            Icon(icon, size: 12, color: fg),
            const SizedBox(width: AppSpacing.xxs),
          ],
          Text(label,
              style: AppType.micro.copyWith(color: fg, letterSpacing: 0.02)),
        ],
      ),
    );
  }
}

/// Status → tone/label mapping used across calls, gateways and lines.
AppBadge statusBadgeFor(BuildContext context, String status) {
  final String s = status.toLowerCase();
  final AppBadgeTone tone = switch (s) {
    'healthy' ||
    'online' ||
    'completed' ||
    'ready' ||
    'running' ||
    'registered' ||
    'ai_resolved' =>
      AppBadgeTone.success,
    'in_progress' ||
    'ringing' ||
    'processing' ||
    'calling' ||
    'queued' ||
    'degraded' ||
    'searching' =>
      AppBadgeTone.info,
    'transferred' ||
    'human_transferred' ||
    'paused' ||
    'scheduled' =>
      AppBadgeTone.accent,
    'unverified' || 'draft' || 'pending' || 'unknown' => AppBadgeTone.neutral,
    'no_answer' ||
    'busy' ||
    'opted_out' ||
    'unregistered' =>
      AppBadgeTone.warning,
    'failed' ||
    'offline' ||
    'cancelled' ||
    'rejected' ||
    'no_sim' =>
      AppBadgeTone.danger,
    _ => AppBadgeTone.neutral,
  };
  final String label = status
      .split('_')
      .map((String w) =>
          w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
      .join(' ');
  return AppBadge(label: label, tone: tone);
}
