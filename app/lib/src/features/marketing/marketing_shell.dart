import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../theme/tokens.dart';
import '../../widgets/primitives.dart';

/// Shared frame for the public marketing pages: top navigation, content, footer.
class MarketingShell extends StatelessWidget {
  const MarketingShell({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Scaffold(
      backgroundColor: p.background,
      body: Column(
        children: <Widget>[
          _MarketingNav(),
          Divider(height: 1, color: p.outline),
          Expanded(
            child: SingleChildScrollView(
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 1120),
                  child: child,
                ),
              ),
            ),
          ),
          const MarketingFooter(),
        ],
      ),
    );
  }
}

class _MarketingNav extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final bool narrow = MediaQuery.sizeOf(context).width < 760;
    return Container(
      height: 64,
      color: p.surface,
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
      child: Row(
        children: <Widget>[
          InkWell(
            onTap: () => context.go('/'),
            child: Row(
              children: <Widget>[
                Container(
                  width: 26,
                  height: 26,
                  decoration: BoxDecoration(
                      color: p.accent, borderRadius: AppRadii.allSm),
                  child: Icon(Icons.graphic_eq, size: 15, color: p.onAccent),
                ),
                const SizedBox(width: AppSpacing.xs),
                Text('ServiceForce.ai',
                    style: AppType.bodyStrong.copyWith(color: p.textPrimary)),
              ],
            ),
          ),
          const Spacer(),
          if (!narrow) ...<Widget>[
            const _NavLink(label: 'Features', route: '/features'),
            const _NavLink(label: 'Pricing', route: '/pricing'),
            const SizedBox(width: AppSpacing.md),
          ],
          AppButton(
            label: 'Sign in',
            variant: AppButtonVariant.ghost,
            size: AppButtonSize.small,
            onPressed: () => context.go('/login'),
          ),
          const SizedBox(width: AppSpacing.xs),
          AppButton(
            label: 'Get started',
            size: AppButtonSize.small,
            onPressed: () => context.go('/signup'),
          ),
        ],
      ),
    );
  }
}

class _NavLink extends StatelessWidget {
  const _NavLink({required this.label, required this.route});

  final String label;
  final String route;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xs),
      child: TextButton(
        onPressed: () => context.go(route),
        child:
            Text(label, style: AppType.body.copyWith(color: p.textSecondary)),
      ),
    );
  }
}

class MarketingFooter extends StatelessWidget {
  const MarketingFooter({super.key});

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Container(
      width: double.infinity,
      color: p.surface,
      padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.lg, vertical: AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Divider(height: 1, color: p.outline),
          const SizedBox(height: AppSpacing.md),
          Row(
            children: <Widget>[
              Text(
                '© 2026 ServiceForce.ai',
                style: AppType.caption.copyWith(color: p.textTertiary),
              ),
              const Spacer(),
              Text(
                'AI voice agents on real phone lines you control',
                style: AppType.caption.copyWith(color: p.textTertiary),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Reusable marketing section with consistent vertical rhythm.
class MarketingSection extends StatelessWidget {
  const MarketingSection({
    super.key,
    required this.child,
    this.eyebrow,
    this.title,
    this.description,
    this.muted = false,
  });

  final Widget child;
  final String? eyebrow;
  final String? title;
  final String? description;
  final bool muted;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Container(
      width: double.infinity,
      color: muted ? p.surface : Colors.transparent,
      padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.lg, vertical: AppSpacing.xxl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          if (eyebrow != null)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.xs),
              child: Text(eyebrow!.toUpperCase(),
                  style: AppType.micro.copyWith(color: p.accent)),
            ),
          if (title != null)
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 640),
              child: Text(title!,
                  style: AppType.display.copyWith(color: p.textPrimary)),
            ),
          if (description != null) ...<Widget>[
            const SizedBox(height: AppSpacing.sm),
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 680),
              child: Text(description!,
                  style: AppType.body
                      .copyWith(color: p.textSecondary, fontSize: 16)),
            ),
          ],
          const SizedBox(height: AppSpacing.xl),
          child,
        ],
      ),
    );
  }
}
