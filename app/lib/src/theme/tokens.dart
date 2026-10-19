import 'package:flutter/material.dart';

/// Spacing scale on a strict 4px grid. Never use raw numbers in widgets.
abstract final class AppSpacing {
  static const double xxs = 4;
  static const double xs = 8;
  static const double sm = 12;
  static const double md = 16;
  static const double lg = 24;
  static const double xl = 32;
  static const double xxl = 48;
  static const double xxxl = 64;
}

/// Corner radii. Three steps only.
abstract final class AppRadii {
  static const Radius sm = Radius.circular(8);
  static const Radius md = Radius.circular(12);
  static const Radius lg = Radius.circular(16);

  static const BorderRadius allSm = BorderRadius.all(sm);
  static const BorderRadius allMd = BorderRadius.all(md);
  static const BorderRadius allLg = BorderRadius.all(lg);
}

/// Motion. Short, eased, and disabled when the OS asks for reduced motion.
abstract final class AppDurations {
  static const Duration fast = Duration(milliseconds: 120);
  static const Duration normal = Duration(milliseconds: 180);
  static const Duration slow = Duration(milliseconds: 280);

  static const Curve ease = Curves.easeOutCubic;
}

/// Type scale. Every size and weight is defined once, here. Widgets must not
/// specify font sizes directly.
abstract final class AppType {
  static const String _family = 'Inter';
  static const List<String> _fallback = <String>[
    'system-ui',
    '-apple-system',
    'Segoe UI',
    'Roboto',
    'Helvetica Neue',
    'Arial',
    'sans-serif',
  ];

  static const TextStyle display = TextStyle(
    fontFamily: _family,
    fontFamilyFallback: _fallback,
    fontSize: 32,
    height: 1.2,
    fontWeight: FontWeight.w600,
    letterSpacing: -0.02,
  );

  static const TextStyle title = TextStyle(
    fontFamily: _family,
    fontFamilyFallback: _fallback,
    fontSize: 24,
    height: 1.25,
    fontWeight: FontWeight.w600,
    letterSpacing: -0.01,
  );

  static const TextStyle heading = TextStyle(
    fontFamily: _family,
    fontFamilyFallback: _fallback,
    fontSize: 20,
    height: 1.3,
    fontWeight: FontWeight.w600,
  );

  static const TextStyle subtitle = TextStyle(
    fontFamily: _family,
    fontFamilyFallback: _fallback,
    fontSize: 16,
    height: 1.4,
    fontWeight: FontWeight.w600,
  );

  static const TextStyle body = TextStyle(
    fontFamily: _family,
    fontFamilyFallback: _fallback,
    fontSize: 14,
    height: 1.5,
    fontWeight: FontWeight.w400,
  );

  static const TextStyle bodyStrong = TextStyle(
    fontFamily: _family,
    fontFamilyFallback: _fallback,
    fontSize: 14,
    height: 1.5,
    fontWeight: FontWeight.w500,
  );

  static const TextStyle label = TextStyle(
    fontFamily: _family,
    fontFamilyFallback: _fallback,
    fontSize: 13,
    height: 1.4,
    fontWeight: FontWeight.w500,
  );

  static const TextStyle caption = TextStyle(
    fontFamily: _family,
    fontFamilyFallback: _fallback,
    fontSize: 12,
    height: 1.45,
    fontWeight: FontWeight.w400,
  );

  static const TextStyle micro = TextStyle(
    fontFamily: _family,
    fontFamilyFallback: _fallback,
    fontSize: 11,
    height: 1.4,
    fontWeight: FontWeight.w600,
    letterSpacing: 0.04,
  );

  /// Monospace for phone numbers, IDs and timings.
  static const TextStyle mono = TextStyle(
    fontFamily: 'JetBrains Mono',
    fontFamilyFallback: <String>[
      'SFMono-Regular',
      'Consolas',
      'Menlo',
      'monospace'
    ],
    fontSize: 13,
    height: 1.45,
    fontWeight: FontWeight.w500,
    fontFeatures: <FontFeature>[FontFeature.tabularFigures()],
  );
}

/// Semantic colour palette. One accent hue, used sparingly.
///
/// Deliberately avoids gradient clichés; every value has a semantic role so
/// themes can be swapped without touching widgets.
@immutable
class AppPalette extends ThemeExtension<AppPalette> {
  const AppPalette({
    required this.background,
    required this.surface,
    required this.surfaceVariant,
    required this.surfaceSunken,
    required this.outline,
    required this.outlineStrong,
    required this.textPrimary,
    required this.textSecondary,
    required this.textTertiary,
    required this.accent,
    required this.accentHover,
    required this.onAccent,
    required this.success,
    required this.successSurface,
    required this.warning,
    required this.warningSurface,
    required this.danger,
    required this.dangerSurface,
    required this.info,
    required this.infoSurface,
    required this.focusRing,
    required this.shadow,
  });

  final Color background;
  final Color surface;
  final Color surfaceVariant;
  final Color surfaceSunken;
  final Color outline;
  final Color outlineStrong;
  final Color textPrimary;
  final Color textSecondary;
  final Color textTertiary;
  final Color accent;
  final Color accentHover;
  final Color onAccent;
  final Color success;
  final Color successSurface;
  final Color warning;
  final Color warningSurface;
  final Color danger;
  final Color dangerSurface;
  final Color info;
  final Color infoSurface;
  final Color focusRing;
  final Color shadow;

  static const AppPalette light = AppPalette(
    background: Color(0xFFF7F8FA),
    surface: Color(0xFFFFFFFF),
    surfaceVariant: Color(0xFFEEF1F5),
    surfaceSunken: Color(0xFFF1F3F7),
    outline: Color(0xFFD7DDE5),
    outlineStrong: Color(0xFFBAC3CE),
    textPrimary: Color(0xFF0F1620),
    textSecondary: Color(0xFF5B6472),
    textTertiary: Color(0xFF8A93A1),
    accent: Color(0xFF0E6E8C),
    accentHover: Color(0xFF0B5A73),
    onAccent: Color(0xFFFFFFFF),
    success: Color(0xFF1E7F4F),
    successSurface: Color(0xFFE6F4EC),
    warning: Color(0xFF9A5B00),
    warningSurface: Color(0xFFFCEFD9),
    danger: Color(0xFFB4232A),
    dangerSurface: Color(0xFFFBE7E8),
    info: Color(0xFF0E6E8C),
    infoSurface: Color(0xFFE3F0F4),
    focusRing: Color(0xFF2E9CBE),
    shadow: Color(0x14101828),
  );

  static const AppPalette dark = AppPalette(
    background: Color(0xFF0E1116),
    surface: Color(0xFF151A21),
    surfaceVariant: Color(0xFF1D242D),
    surfaceSunken: Color(0xFF11161C),
    outline: Color(0xFF2A3340),
    outlineStrong: Color(0xFF3A4553),
    textPrimary: Color(0xFFE6EAF0),
    textSecondary: Color(0xFFA7B0BD),
    textTertiary: Color(0xFF7A8492),
    accent: Color(0xFF4FB3CE),
    accentHover: Color(0xFF6BC4DC),
    onAccent: Color(0xFF04212B),
    success: Color(0xFF5BC48C),
    successSurface: Color(0xFF14301F),
    warning: Color(0xFFE0A45C),
    warningSurface: Color(0xFF33260D),
    danger: Color(0xFFF08A8F),
    dangerSurface: Color(0xFF341518),
    info: Color(0xFF4FB3CE),
    infoSurface: Color(0xFF122A33),
    focusRing: Color(0xFF6BC4DC),
    shadow: Color(0x66000000),
  );

  @override
  AppPalette copyWith({
    Color? background,
    Color? surface,
    Color? surfaceVariant,
    Color? surfaceSunken,
    Color? outline,
    Color? outlineStrong,
    Color? textPrimary,
    Color? textSecondary,
    Color? textTertiary,
    Color? accent,
    Color? accentHover,
    Color? onAccent,
    Color? success,
    Color? successSurface,
    Color? warning,
    Color? warningSurface,
    Color? danger,
    Color? dangerSurface,
    Color? info,
    Color? infoSurface,
    Color? focusRing,
    Color? shadow,
  }) {
    return AppPalette(
      background: background ?? this.background,
      surface: surface ?? this.surface,
      surfaceVariant: surfaceVariant ?? this.surfaceVariant,
      surfaceSunken: surfaceSunken ?? this.surfaceSunken,
      outline: outline ?? this.outline,
      outlineStrong: outlineStrong ?? this.outlineStrong,
      textPrimary: textPrimary ?? this.textPrimary,
      textSecondary: textSecondary ?? this.textSecondary,
      textTertiary: textTertiary ?? this.textTertiary,
      accent: accent ?? this.accent,
      accentHover: accentHover ?? this.accentHover,
      onAccent: onAccent ?? this.onAccent,
      success: success ?? this.success,
      successSurface: successSurface ?? this.successSurface,
      warning: warning ?? this.warning,
      warningSurface: warningSurface ?? this.warningSurface,
      danger: danger ?? this.danger,
      dangerSurface: dangerSurface ?? this.dangerSurface,
      info: info ?? this.info,
      infoSurface: infoSurface ?? this.infoSurface,
      focusRing: focusRing ?? this.focusRing,
      shadow: shadow ?? this.shadow,
    );
  }

  @override
  AppPalette lerp(ThemeExtension<AppPalette>? other, double t) {
    if (other is! AppPalette) return this;
    return AppPalette(
      background: Color.lerp(background, other.background, t)!,
      surface: Color.lerp(surface, other.surface, t)!,
      surfaceVariant: Color.lerp(surfaceVariant, other.surfaceVariant, t)!,
      surfaceSunken: Color.lerp(surfaceSunken, other.surfaceSunken, t)!,
      outline: Color.lerp(outline, other.outline, t)!,
      outlineStrong: Color.lerp(outlineStrong, other.outlineStrong, t)!,
      textPrimary: Color.lerp(textPrimary, other.textPrimary, t)!,
      textSecondary: Color.lerp(textSecondary, other.textSecondary, t)!,
      textTertiary: Color.lerp(textTertiary, other.textTertiary, t)!,
      accent: Color.lerp(accent, other.accent, t)!,
      accentHover: Color.lerp(accentHover, other.accentHover, t)!,
      onAccent: Color.lerp(onAccent, other.onAccent, t)!,
      success: Color.lerp(success, other.success, t)!,
      successSurface: Color.lerp(successSurface, other.successSurface, t)!,
      warning: Color.lerp(warning, other.warning, t)!,
      warningSurface: Color.lerp(warningSurface, other.warningSurface, t)!,
      danger: Color.lerp(danger, other.danger, t)!,
      dangerSurface: Color.lerp(dangerSurface, other.dangerSurface, t)!,
      info: Color.lerp(info, other.info, t)!,
      infoSurface: Color.lerp(infoSurface, other.infoSurface, t)!,
      focusRing: Color.lerp(focusRing, other.focusRing, t)!,
      shadow: Color.lerp(shadow, other.shadow, t)!,
    );
  }
}

/// Convenience accessor so widgets read palette values consistently.
extension AppPaletteContext on BuildContext {
  AppPalette get palette =>
      Theme.of(this).extension<AppPalette>() ?? AppPalette.light;
}
