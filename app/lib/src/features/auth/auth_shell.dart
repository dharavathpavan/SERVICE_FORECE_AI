import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../theme/tokens.dart';

/// Split layout used by sign-in and sign-up: form on the left, brand panel on
/// the right. Collapses to a single column on narrow screens.
class AuthShell extends StatelessWidget {
  const AuthShell({
    super.key,
    required this.title,
    required this.subtitle,
    required this.form,
    required this.footer,
  });

  final String title;
  final String subtitle;
  final Widget form;
  final Widget footer;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final bool narrow = MediaQuery.sizeOf(context).width < 900;

    return Scaffold(
      backgroundColor: p.background,
      body: Row(
        children: <Widget>[
          Expanded(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(AppSpacing.lg),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 400),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      InkWell(
                        onTap: () => context.go('/'),
                        child: Row(
                          children: <Widget>[
                            Container(
                              width: 26,
                              height: 26,
                              decoration: BoxDecoration(
                                  color: p.accent,
                                  borderRadius: AppRadii.allSm),
                              child: Icon(Icons.graphic_eq,
                                  size: 15, color: p.onAccent),
                            ),
                            const SizedBox(width: AppSpacing.xs),
                            Text('ServiceForce.ai',
                                style: AppType.bodyStrong
                                    .copyWith(color: p.textPrimary)),
                          ],
                        ),
                      ),
                      const SizedBox(height: AppSpacing.xl),
                      Text(title,
                          style: AppType.title.copyWith(color: p.textPrimary)),
                      const SizedBox(height: AppSpacing.xxs),
                      Text(subtitle,
                          style: AppType.body.copyWith(color: p.textSecondary)),
                      const SizedBox(height: AppSpacing.lg),
                      form,
                      const SizedBox(height: AppSpacing.lg),
                      footer,
                    ],
                  ),
                ),
              ),
            ),
          ),
          if (!narrow) const Expanded(child: _BrandPanel()),
        ],
      ),
    );
  }
}

class _BrandPanel extends StatelessWidget {
  const _BrandPanel();

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Container(
      color: p.surface,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xxl),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            Text(
              'Answer every call — even at 2am.',
              style: AppType.display.copyWith(color: p.textPrimary),
            ),
            const SizedBox(height: AppSpacing.md),
            Text(
              'ServiceForce.ai connects your AI agent to a real business line and keeps a '
              'truthful record of how every conversation ended.',
              style: AppType.body
                  .copyWith(color: p.textSecondary, fontSize: 15, height: 1.6),
            ),
            const SizedBox(height: AppSpacing.xl),
            const _PanelPoint(
                icon: Icons.verified_outlined,
                text: 'Line state verified by an active probe'),
            const _PanelPoint(
                icon: Icons.bolt_outlined,
                text: 'Barge-in ready voice orchestration'),
            const _PanelPoint(
                icon: Icons.receipt_long_outlined,
                text: 'Audit trail on every privileged action'),
          ],
        ),
      ),
    );
  }
}

class _PanelPoint extends StatelessWidget {
  const _PanelPoint({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Row(
        children: <Widget>[
          Icon(icon, size: 16, color: p.accent),
          const SizedBox(width: AppSpacing.xs),
          Expanded(
              child: Text(text,
                  style: AppType.body.copyWith(color: p.textSecondary))),
        ],
      ),
    );
  }
}
