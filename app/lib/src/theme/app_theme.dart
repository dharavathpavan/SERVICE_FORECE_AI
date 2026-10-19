import 'package:flutter/material.dart';

import 'tokens.dart';

/// Builds the Material theme from our tokens.
abstract final class AppTheme {
  static ThemeData light() => _build(AppPalette.light, Brightness.light);
  static ThemeData dark() => _build(AppPalette.dark, Brightness.dark);

  static ThemeData _build(AppPalette p, Brightness brightness) {
    final ColorScheme scheme = ColorScheme(
      brightness: brightness,
      primary: p.accent,
      onPrimary: p.onAccent,
      secondary: p.accent,
      onSecondary: p.onAccent,
      error: p.danger,
      onError: Colors.white,
      surface: p.surface,
      onSurface: p.textPrimary,
      surfaceContainerHighest: p.surfaceVariant,
      outline: p.outline,
      outlineVariant: p.outlineStrong,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: scheme,
      scaffoldBackgroundColor: p.background,
      canvasColor: p.background,
      fontFamily: AppType.body.fontFamily,
      fontFamilyFallback: AppType.body.fontFamilyFallback,
      extensions: <ThemeExtension<dynamic>>[p],
      splashFactory: InkSparkle.splashFactory,
      dividerTheme: DividerThemeData(color: p.outline, thickness: 1, space: 1),
      iconTheme: IconThemeData(color: p.textSecondary, size: 18),
      textTheme: TextTheme(
        displaySmall: AppType.display.copyWith(color: p.textPrimary),
        headlineMedium: AppType.title.copyWith(color: p.textPrimary),
        headlineSmall: AppType.heading.copyWith(color: p.textPrimary),
        titleMedium: AppType.subtitle.copyWith(color: p.textPrimary),
        bodyLarge: AppType.bodyStrong.copyWith(color: p.textPrimary),
        bodyMedium: AppType.body.copyWith(color: p.textPrimary),
        bodySmall: AppType.caption.copyWith(color: p.textSecondary),
        labelLarge: AppType.label.copyWith(color: p.textPrimary),
        labelSmall: AppType.micro.copyWith(color: p.textSecondary),
      ),
      // Explicit focus indicators for keyboard users.
      focusColor: p.focusRing.withValues(alpha: 0.28),
      hoverColor: p.surfaceVariant.withValues(alpha: 0.6),
      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(
          color: p.textPrimary,
          borderRadius: AppRadii.allSm,
        ),
        textStyle: AppType.caption.copyWith(color: p.surface),
        waitDuration: AppDurations.slow,
      ),
      scrollbarTheme: ScrollbarThemeData(
        thickness: WidgetStateProperty.all(8),
        radius: AppRadii.sm,
        thumbColor: WidgetStateProperty.all(p.outlineStrong),
      ),
    );
  }
}
