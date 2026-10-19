import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../theme/tokens.dart';
import '../../widgets/primitives.dart';
import 'marketing_shell.dart';

class FeaturesPage extends StatelessWidget {
  const FeaturesPage({super.key});

  @override
  Widget build(BuildContext context) {
    return const MarketingShell(
      child: Column(
        children: <Widget>[
          MarketingSection(
            eyebrow: 'Features',
            title: 'Built for real calls, not demos',
            description:
                'Every capability below is enforced server-side and reflected honestly in the interface.',
            child: _FeatureDetailList(),
          ),
        ],
      ),
    );
  }
}

class _FeatureDetailList extends StatelessWidget {
  const _FeatureDetailList();

  @override
  Widget build(BuildContext context) {
    const List<(String, List<String>)> groups = <(String, List<String>)>[
      (
        'Conversation',
        <String>[
          'Multi-turn agents with per-agent prompt, greeting, voice and language',
          'Retrieval-grounded answers from your uploaded PDF, DOCX and text documents',
          'Barge-in support where the voice provider and audio bridge allow it',
          'Configurable maximum call duration and graceful wrap-up',
        ]
      ),
      (
        'Telephony',
        <String>[
          'Inbound answering on a DID mapped to your workspace',
          'Manual outbound calls and paced outbound campaigns',
          'Live SIM and line status from the gateway, verified by an active probe',
          'Capability reporting that states what your hardware cannot do',
        ]
      ),
      (
        'Tools and automation',
        <String>[
          'Live API tools with SSRF protection and write-action confirmation',
          'Warm transfer to a human number, voicemail, or a polite close',
          'Campaign retries, concurrency limits and calling windows',
        ]
      ),
      (
        'Compliance and governance',
        <String>[
          'Consent capture and do-not-call suppression lists',
          'Server-side monthly caps, budgets and calling-hour enforcement',
          'Tamper-evident audit log for every privileged action',
        ]
      ),
    ];

    return Column(
      children: <Widget>[
        for (final (String title, List<String> points) g in groups) ...<Widget>[
          _FeatureGroup(title: g.$1, points: g.$2),
          const SizedBox(height: AppSpacing.md),
        ],
        Align(
          alignment: Alignment.centerLeft,
          child: AppButton(
            label: 'Create a workspace',
            onPressed: () => context.go('/signup'),
          ),
        ),
      ],
    );
  }
}

class _FeatureGroup extends StatelessWidget {
  const _FeatureGroup({required this.title, required this.points});

  final String title;
  final List<String> points;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        color: p.surface,
        borderRadius: AppRadii.allMd,
        border: Border.all(color: p.outline),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: AppType.subtitle.copyWith(color: p.textPrimary)),
          const SizedBox(height: AppSpacing.sm),
          for (final String point in points)
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
                      child: Text(point,
                          style:
                              AppType.body.copyWith(color: p.textSecondary))),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
