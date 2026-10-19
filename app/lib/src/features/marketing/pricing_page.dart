import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../theme/tokens.dart';
import '../../widgets/primitives.dart';
import 'marketing_shell.dart';

class PricingPage extends StatelessWidget {
  const PricingPage({super.key});

  @override
  Widget build(BuildContext context) {
    return MarketingShell(
      child: MarketingSection(
        eyebrow: 'Pricing',
        title: 'Plans that scale with your call volume',
        description:
            'Telephony is billed by your carrier. ServiceForce.ai charges for the platform and usage.',
        child: LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            const List<_Plan> plans = <_Plan>[
              _Plan(
                name: 'Starter',
                price: r'$49',
                cadence: '/ month',
                summary: 'For a single line and light inbound volume.',
                features: <String>[
                  '1 phone line',
                  '500 calls / month',
                  '1 knowledge base',
                  'Call transcripts and summaries',
                  'Email support',
                ],
              ),
              _Plan(
                name: 'Growth',
                price: r'$149',
                cadence: '/ month',
                summary: 'For teams running inbound and outbound together.',
                highlighted: true,
                features: <String>[
                  'Up to 5 phone lines',
                  '5,000 calls / month',
                  'Unlimited knowledge bases',
                  'Outbound campaigns',
                  'Human transfer and voicemail',
                  'Priority support',
                ],
              ),
              _Plan(
                name: 'Scale',
                price: 'Custom',
                cadence: '',
                summary: 'For high-volume operations and custom gateways.',
                features: <String>[
                  'Unlimited lines',
                  'Volume call pricing',
                  'Multi-workspace tenancy',
                  'SSO and audit exports',
                  'Dedicated onboarding',
                ],
              ),
            ];

            final int columns = constraints.maxWidth > 900 ? 3 : 1;
            const double spacing = AppSpacing.md;
            final double width =
                (constraints.maxWidth - (spacing * (columns - 1))) / columns;
            return Wrap(
              spacing: spacing,
              runSpacing: spacing,
              children: <Widget>[
                for (final _Plan plan in plans)
                  SizedBox(width: width, child: _PlanCard(plan: plan)),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _Plan {
  const _Plan({
    required this.name,
    required this.price,
    required this.cadence,
    required this.summary,
    required this.features,
    this.highlighted = false,
  });

  final String name;
  final String price;
  final String cadence;
  final String summary;
  final List<String> features;
  final bool highlighted;
}

class _PlanCard extends StatelessWidget {
  const _PlanCard({required this.plan});

  final _Plan plan;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Container(
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        color: p.surface,
        borderRadius: AppRadii.allMd,
        border: Border.all(
            color: plan.highlighted ? p.accent : p.outline,
            width: plan.highlighted ? 1.5 : 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Text(plan.name,
                  style: AppType.subtitle.copyWith(color: p.textPrimary)),
              if (plan.highlighted) ...<Widget>[
                const SizedBox(width: AppSpacing.xs),
                const AppBadge(label: 'Popular', tone: AppBadgeTone.accent),
              ],
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: <Widget>[
              Text(plan.price,
                  style: AppType.display.copyWith(color: p.textPrimary)),
              if (plan.cadence.isNotEmpty) ...<Widget>[
                const SizedBox(width: AppSpacing.xxs),
                Text(plan.cadence,
                    style: AppType.caption.copyWith(color: p.textTertiary)),
              ],
            ],
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(plan.summary,
              style: AppType.body.copyWith(color: p.textSecondary)),
          const SizedBox(height: AppSpacing.md),
          Divider(height: 1, color: p.outline),
          const SizedBox(height: AppSpacing.md),
          for (final String feature in plan.features)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.xs),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Padding(
                    padding: const EdgeInsets.only(top: 3),
                    child: Icon(Icons.check, size: 15, color: p.success),
                  ),
                  const SizedBox(width: AppSpacing.xs),
                  Expanded(
                      child: Text(feature,
                          style:
                              AppType.body.copyWith(color: p.textSecondary))),
                ],
              ),
            ),
          const SizedBox(height: AppSpacing.md),
          AppButton(
            label: plan.name == 'Scale' ? 'Contact sales' : 'Start free',
            expand: true,
            variant: plan.highlighted
                ? AppButtonVariant.primary
                : AppButtonVariant.secondary,
            onPressed: () => context.go('/signup'),
          ),
        ],
      ),
    );
  }
}
