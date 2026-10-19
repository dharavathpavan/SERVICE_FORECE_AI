import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../theme/tokens.dart';
import '../../widgets/primitives.dart';
import 'marketing_shell.dart';

class LandingPage extends StatelessWidget {
  const LandingPage({super.key});

  @override
  Widget build(BuildContext context) {
    return const MarketingShell(
      child: Column(
        children: <Widget>[
          _Hero(),
          _ProductPreview(),
          MarketingSection(
            muted: true,
            eyebrow: 'Platform',
            title: 'Everything an AI phone agent needs, in one place',
            description:
                'Agents, knowledge, tools, telephony and analytics are wired together — so a call '
                'can look something up, take an action, and hand off to a human when it should.',
            child: _FeatureGrid(),
          ),
          MarketingSection(
            eyebrow: 'How it works',
            title: 'From SIM to conversation in four steps',
            child: _HowItWorks(),
          ),
          _TelephonyReality(),
          _CallToAction(),
        ],
      ),
    );
  }
}

class _Hero extends StatelessWidget {
  const _Hero();

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Padding(
      padding: const EdgeInsets.fromLTRB(
          AppSpacing.lg, AppSpacing.xxxl, AppSpacing.lg, AppSpacing.xl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.sm, vertical: AppSpacing.xxs),
            decoration: BoxDecoration(
              color: p.infoSurface,
              borderRadius: AppRadii.allSm,
              border: Border.all(color: p.accent.withValues(alpha: 0.25)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Container(
                    width: 6,
                    height: 6,
                    decoration:
                        BoxDecoration(color: p.accent, shape: BoxShape.circle)),
                const SizedBox(width: AppSpacing.xs),
                Text(
                  'Physical SIM · GSM / VoLTE gateways · bring your own number',
                  style: AppType.caption.copyWith(color: p.accent),
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 760),
            child: Text(
              'AI voice agents that answer your real business line',
              style: AppType.display.copyWith(
                color: p.textPrimary,
                fontSize: MediaQuery.sizeOf(context).width < 760 ? 30 : 40,
                height: 1.15,
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 620),
            child: Text(
              'ServiceForce.ai runs inbound and outbound calls through your own SIM and voice gateway. '
              'The agent retrieves your knowledge, calls your business tools, transfers to a human when '
              'asked, and records exactly why every call succeeded or failed.',
              style: AppType.body
                  .copyWith(color: p.textSecondary, fontSize: 16, height: 1.6),
            ),
          ),
          const SizedBox(height: AppSpacing.lg),
          Row(
            children: <Widget>[
              AppButton(
                label: 'Start free',
                trailingIcon: Icons.arrow_forward,
                onPressed: () => context.go('/signup'),
              ),
              const SizedBox(width: AppSpacing.sm),
              AppButton(
                label: 'Explore the platform',
                variant: AppButtonVariant.secondary,
                onPressed: () => context.go('/features'),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Text(
            'No credit card. Your workspace is ready the moment you sign up.',
            style: AppType.caption.copyWith(color: p.textTertiary),
          ),
        ],
      ),
    );
  }
}

/// A literal, believable render of the product rather than a stock illustration.
class _ProductPreview extends StatelessWidget {
  const _ProductPreview();

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
      child: Container(
        decoration: BoxDecoration(
          color: p.surface,
          borderRadius: AppRadii.allLg,
          border: Border.all(color: p.outline),
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(
          children: <Widget>[
            Container(
              height: 40,
              color: p.surfaceSunken,
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
              child: Row(
                children: <Widget>[
                  for (int i = 0; i < 3; i++)
                    Padding(
                      padding: const EdgeInsets.only(right: AppSpacing.xs),
                      child: Container(
                        width: 9,
                        height: 9,
                        decoration: BoxDecoration(
                            color: p.outlineStrong, shape: BoxShape.circle),
                      ),
                    ),
                  const SizedBox(width: AppSpacing.sm),
                  Text('serviceforce.ai/app',
                      style: AppType.caption.copyWith(color: p.textTertiary)),
                  const Spacer(),
                  const AppBadge(
                      label: 'Provider: mock', icon: Icons.router_outlined),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Column(
                children: <Widget>[
                  const Row(
                    children: <Widget>[
                      Expanded(
                          child:
                              _PreviewStat(label: 'Calls today', value: '128')),
                      SizedBox(width: AppSpacing.sm),
                      Expanded(
                          child:
                              _PreviewStat(label: 'AI resolved', value: '82%')),
                      SizedBox(width: AppSpacing.sm),
                      Expanded(
                          child: _PreviewStat(
                              label: 'Avg. duration', value: '2m 41s')),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.md),
                  Container(
                    decoration: BoxDecoration(
                      border: Border.all(color: p.outline),
                      borderRadius: AppRadii.allMd,
                    ),
                    child: Column(
                      children: <Widget>[
                        const _PreviewRow(
                          caller: '+1 555 0199',
                          summary: 'Order ORD-8921 status enquiry',
                          status: 'Completed',
                          tone: AppBadgeTone.success,
                        ),
                        Divider(height: 1, color: p.outline),
                        const _PreviewRow(
                          caller: '+1 555 0142',
                          summary: 'Appointment booked for Friday 10:00',
                          status: 'Completed',
                          tone: AppBadgeTone.success,
                        ),
                        Divider(height: 1, color: p.outline),
                        const _PreviewRow(
                          caller: '+1 555 0173',
                          summary: 'Requested a human — transferred',
                          status: 'Transferred',
                          tone: AppBadgeTone.accent,
                        ),
                        Divider(height: 1, color: p.outline),
                        const _PreviewRow(
                          caller: '+1 555 0128',
                          summary: 'Carrier rejected the call',
                          status: 'Failed',
                          tone: AppBadgeTone.danger,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PreviewStat extends StatelessWidget {
  const _PreviewStat({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Container(
      padding: const EdgeInsets.all(AppSpacing.sm),
      decoration:
          BoxDecoration(color: p.surfaceSunken, borderRadius: AppRadii.allSm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: AppType.caption.copyWith(color: p.textSecondary)),
          const SizedBox(height: AppSpacing.xxs),
          Text(value, style: AppType.heading.copyWith(color: p.textPrimary)),
        ],
      ),
    );
  }
}

class _PreviewRow extends StatelessWidget {
  const _PreviewRow({
    required this.caller,
    required this.summary,
    required this.status,
    required this.tone,
  });

  final String caller;
  final String summary;
  final String status;
  final AppBadgeTone tone;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Padding(
      padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md, vertical: AppSpacing.sm),
      child: Row(
        children: <Widget>[
          Icon(Icons.call_outlined, size: 15, color: p.textTertiary),
          const SizedBox(width: AppSpacing.xs),
          SizedBox(
            width: 130,
            child: Text(caller,
                style: AppType.mono.copyWith(color: p.textPrimary)),
          ),
          Expanded(
            child: Text(
              summary,
              style: AppType.body.copyWith(color: p.textSecondary),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          AppBadge(label: status, tone: tone),
        ],
      ),
    );
  }
}

class _FeatureGrid extends StatelessWidget {
  const _FeatureGrid();

  @override
  Widget build(BuildContext context) {
    const List<(IconData, String, String)> features =
        <(IconData, String, String)>[
      (
        Icons.psychology_outlined,
        'Agents that know your business',
        'Prompt, voice, language, greeting and fallback are versioned per agent. '
            'Retrieval grounding keeps answers tied to your documents.'
      ),
      (
        Icons.build_outlined,
        'Tools with real guardrails',
        'Agents call your live APIs through a tool router with SSRF protection, '
            'write-action confirmation and a full audit trail.'
      ),
      (
        Icons.router_outlined,
        'Telephony you actually own',
        'Register GSM/VoLTE gateways, verify each SIM with a real probe, and see '
            'honest line state instead of an assumed connection.'
      ),
      (
        Icons.call_split_outlined,
        'Graceful human handoff',
        'Warm transfer to a human destination, voicemail or a polite close — '
            'every fallback is configured and every outcome is recorded.'
      ),
      (
        Icons.insights_outlined,
        'Measured analytics',
        'Answered, resolved, transferred and failed are counted separately so the '
            'numbers reflect reality, not optimism.'
      ),
      (
        Icons.receipt_long_outlined,
        'Compliance built in',
        'Consent, DNC suppression, calling windows, monthly caps and per-action '
            'audit logging enforced server-side.'
      ),
    ];

    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final int columns = constraints.maxWidth > 900
            ? 3
            : (constraints.maxWidth > 600 ? 2 : 1);
        const double spacing = AppSpacing.md;
        final double width =
            (constraints.maxWidth - (spacing * (columns - 1))) / columns;
        return Wrap(
          spacing: spacing,
          runSpacing: spacing,
          children: <Widget>[
            for (final (IconData icon, String title, String body) f in features)
              SizedBox(
                width: width,
                child: _FeatureCard(icon: f.$1, title: f.$2, body: f.$3),
              ),
          ],
        );
      },
    );
  }
}

class _FeatureCard extends StatelessWidget {
  const _FeatureCard(
      {required this.icon, required this.title, required this.body});

  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
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
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
                color: p.infoSurface, borderRadius: AppRadii.allSm),
            child: Icon(icon, size: 17, color: p.accent),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(title, style: AppType.subtitle.copyWith(color: p.textPrimary)),
          const SizedBox(height: AppSpacing.xxs),
          Text(body,
              style:
                  AppType.body.copyWith(color: p.textSecondary, height: 1.55)),
        ],
      ),
    );
  }
}

class _HowItWorks extends StatelessWidget {
  const _HowItWorks();

  @override
  Widget build(BuildContext context) {
    const List<(String, String)> steps = <(String, String)>[
      (
        'Connect your number',
        'Bring a SIM behind a GSM/VoLTE gateway and register the SIP endpoint.'
      ),
      (
        'Verify the line',
        'A real probe confirms the SIM is registered before any call is placed.'
      ),
      (
        'Configure the agent',
        'Write the prompt, attach knowledge, choose the voice and tools.'
      ),
      (
        'Go live',
        'Inbound answers automatically; outbound runs manually or as a campaign.'
      ),
    ];

    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final int columns = constraints.maxWidth > 800
            ? 4
            : (constraints.maxWidth > 520 ? 2 : 1);
        const double spacing = AppSpacing.md;
        final double width =
            (constraints.maxWidth - (spacing * (columns - 1))) / columns;
        return Wrap(
          spacing: spacing,
          runSpacing: spacing,
          children: <Widget>[
            for (int i = 0; i < steps.length; i++)
              SizedBox(
                width: width,
                child: _StepCard(
                    index: i + 1, title: steps[i].$1, body: steps[i].$2),
              ),
          ],
        );
      },
    );
  }
}

class _StepCard extends StatelessWidget {
  const _StepCard(
      {required this.index, required this.title, required this.body});

  final int index;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Container(
          width: 28,
          height: 28,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: p.surface,
            borderRadius: AppRadii.allSm,
            border: Border.all(color: p.outlineStrong),
          ),
          child: Text('$index',
              style: AppType.label.copyWith(color: p.textPrimary)),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(title, style: AppType.bodyStrong.copyWith(color: p.textPrimary)),
        const SizedBox(height: AppSpacing.xxs),
        Text(body,
            style: AppType.body.copyWith(color: p.textSecondary, height: 1.5)),
      ],
    );
  }
}

/// States the hardware reality plainly. We would rather set expectations than
/// promise something the architecture cannot deliver.
class _TelephonyReality extends StatelessWidget {
  const _TelephonyReality();

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Padding(
      padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.lg, vertical: AppSpacing.xxl),
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.lg),
        decoration: BoxDecoration(
          color: p.warningSurface,
          borderRadius: AppRadii.allMd,
          border: Border.all(color: p.warning.withValues(alpha: 0.3)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                Icon(Icons.info_outline, size: 18, color: p.warning),
                const SizedBox(width: AppSpacing.xs),
                Text('An honest note about hardware',
                    style: AppType.subtitle.copyWith(color: p.textPrimary)),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              'Real-time AI speech with barge-in needs low-latency, full-duplex PCM audio on the line. '
              'A consumer smartphone does not expose that, so a phone alone cannot act as a voice gateway. '
              'ServiceForce.ai supports SIMs behind dedicated GSM/VoLTE gateways (Yeastar TG, Dinstar UC2000 '
              'class) that terminate SIP into Asterisk. The app reports what your hardware actually supports — '
              'including when it does not support something.',
              style: AppType.body.copyWith(color: p.textPrimary, height: 1.6),
            ),
          ],
        ),
      ),
    );
  }
}

class _CallToAction extends StatelessWidget {
  const _CallToAction();

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Container(
      width: double.infinity,
      color: p.surface,
      padding: const EdgeInsets.all(AppSpacing.xxl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Put an AI agent on your line today',
              style: AppType.title.copyWith(color: p.textPrimary)),
          const SizedBox(height: AppSpacing.xs),
          Text(
            'Create a workspace, add an agent, and place a test call against the mock provider before '
            'you connect hardware.',
            style: AppType.body.copyWith(color: p.textSecondary),
          ),
          const SizedBox(height: AppSpacing.md),
          AppButton(
            label: 'Create your workspace',
            onPressed: () => context.go('/signup'),
          ),
        ],
      ),
    );
  }
}
