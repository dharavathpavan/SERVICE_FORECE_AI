import 'package:flutter/material.dart';

import '../theme/tokens.dart';

/// Labelled text field with inline validation and a consistent 40px control height.
class AppTextField extends StatelessWidget {
  const AppTextField({
    super.key,
    required this.label,
    required this.controller,
    this.hint,
    this.helper,
    this.error,
    this.obscure = false,
    this.enabled = true,
    this.keyboardType,
    this.maxLines = 1,
    this.prefixIcon,
    this.autofillHints,
    this.onSubmitted,
    this.textInputAction,
  });

  final String label;
  final TextEditingController controller;
  final String? hint;
  final String? helper;
  final String? error;
  final bool obscure;
  final bool enabled;
  final TextInputType? keyboardType;
  final int maxLines;
  final IconData? prefixIcon;
  final Iterable<String>? autofillHints;
  final ValueChanged<String>? onSubmitted;
  final TextInputAction? textInputAction;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(label, style: AppType.label.copyWith(color: p.textSecondary)),
        const SizedBox(height: AppSpacing.xxs),
        TextField(
          controller: controller,
          obscureText: obscure,
          enabled: enabled,
          keyboardType: keyboardType,
          maxLines: obscure ? 1 : maxLines,
          autofillHints: autofillHints,
          onSubmitted: onSubmitted,
          textInputAction: textInputAction,
          style: AppType.body.copyWith(color: p.textPrimary),
          decoration: InputDecoration(
            isDense: true,
            hintText: hint,
            hintStyle: AppType.body.copyWith(color: p.textTertiary),
            prefixIcon: prefixIcon != null
                ? Icon(prefixIcon, size: 16, color: p.textTertiary)
                : null,
            contentPadding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.sm, vertical: AppSpacing.sm),
            filled: true,
            fillColor: enabled ? p.surface : p.surfaceSunken,
            border: OutlineInputBorder(
              borderRadius: AppRadii.allSm,
              borderSide:
                  BorderSide(color: error != null ? p.danger : p.outline),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: AppRadii.allSm,
              borderSide:
                  BorderSide(color: error != null ? p.danger : p.outline),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: AppRadii.allSm,
              borderSide: BorderSide(color: p.accent, width: 1.5),
            ),
            errorBorder: OutlineInputBorder(
              borderRadius: AppRadii.allSm,
              borderSide: BorderSide(color: p.danger),
            ),
          ),
        ),
        if (error != null)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.xxs),
            child:
                Text(error!, style: AppType.caption.copyWith(color: p.danger)),
          )
        else if (helper != null)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.xxs),
            child: Text(helper!,
                style: AppType.caption.copyWith(color: p.textTertiary)),
          ),
      ],
    );
  }
}

/// Labelled dropdown for enum-ish choices.
class AppSelect<T> extends StatelessWidget {
  const AppSelect({
    super.key,
    required this.label,
    required this.value,
    required this.items,
    required this.onChanged,
    this.helper,
  });

  final String label;
  final T value;
  final List<DropdownMenuItem<T>> items;
  final ValueChanged<T?> onChanged;
  final String? helper;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(label, style: AppType.label.copyWith(color: p.textSecondary)),
        const SizedBox(height: AppSpacing.xxs),
        DropdownButtonFormField<T>(
          initialValue: value,
          items: items,
          onChanged: onChanged,
          isDense: true,
          style: AppType.body.copyWith(color: p.textPrimary),
          dropdownColor: p.surface,
          icon: Icon(Icons.expand_more, size: 18, color: p.textTertiary),
          decoration: InputDecoration(
            isDense: true,
            contentPadding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.sm, vertical: AppSpacing.sm),
            filled: true,
            fillColor: p.surface,
            border: OutlineInputBorder(
                borderRadius: AppRadii.allSm,
                borderSide: BorderSide(color: p.outline)),
            enabledBorder: OutlineInputBorder(
                borderRadius: AppRadii.allSm,
                borderSide: BorderSide(color: p.outline)),
            focusedBorder: OutlineInputBorder(
                borderRadius: AppRadii.allSm,
                borderSide: BorderSide(color: p.accent, width: 1.5)),
          ),
        ),
        if (helper != null)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.xxs),
            child: Text(helper!,
                style: AppType.caption.copyWith(color: p.textTertiary)),
          ),
      ],
    );
  }
}

/// Row-style boolean toggle with a description.
class AppSwitchRow extends StatelessWidget {
  const AppSwitchRow({
    super.key,
    required this.title,
    required this.value,
    required this.onChanged,
    this.description,
  });

  final String title;
  final bool value;
  final ValueChanged<bool> onChanged;
  final String? description;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xxs),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(title,
                    style: AppType.bodyStrong.copyWith(color: p.textPrimary)),
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
          const SizedBox(width: AppSpacing.sm),
          Switch(value: value, onChanged: onChanged),
        ],
      ),
    );
  }
}

/// Number/label statistic tile used on dashboards.
class StatTile extends StatelessWidget {
  const StatTile({
    super.key,
    required this.label,
    required this.value,
    this.delta,
    this.deltaTone = StatDeltaTone.neutral,
    this.icon,
  });

  final String label;
  final String value;
  final String? delta;
  final StatDeltaTone deltaTone;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final Color deltaColor = switch (deltaTone) {
      StatDeltaTone.up => p.success,
      StatDeltaTone.down => p.danger,
      StatDeltaTone.neutral => p.textTertiary,
    };
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: p.surface,
        borderRadius: AppRadii.allMd,
        border: Border.all(color: p.outline),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                  child: Text(label,
                      style: AppType.caption.copyWith(color: p.textSecondary))),
              if (icon != null) Icon(icon, size: 15, color: p.textTertiary),
            ],
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(value, style: AppType.heading.copyWith(color: p.textPrimary)),
          if (delta != null) ...<Widget>[
            const SizedBox(height: AppSpacing.xxs),
            Text(delta!, style: AppType.caption.copyWith(color: deltaColor)),
          ],
        ],
      ),
    );
  }
}

enum StatDeltaTone { up, down, neutral }

/// Key/value row for detail panels.
class DetailRow extends StatelessWidget {
  const DetailRow(
      {super.key, required this.label, required this.value, this.mono = false});

  final String label;
  final String value;
  final bool mono;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xxs),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          SizedBox(
            width: 160,
            child: Text(label,
                style: AppType.caption.copyWith(color: p.textSecondary)),
          ),
          Expanded(
            child: Text(
              value,
              style: (mono ? AppType.mono : AppType.body)
                  .copyWith(color: p.textPrimary),
            ),
          ),
        ],
      ),
    );
  }
}
