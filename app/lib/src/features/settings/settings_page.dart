import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../api/api_client.dart';
import '../../api/api_error.dart';
import '../../api/models.dart';
import '../../state/providers.dart';
import '../../theme/tokens.dart';
import '../../widgets/async_view.dart';
import '../../widgets/inputs.dart';
import '../../widgets/primitives.dart';
import '../../widgets/surfaces.dart';

class SettingsPage extends ConsumerWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AppPalette p = context.palette;
    final AuthState auth = ref.watch(authProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const PageHeader(
          eyebrow: 'Administration',
          title: 'Settings',
          description:
              'Workspace details, appearance and the honest state of the platform integrations.',
        ),
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final bool stacked = constraints.maxWidth < 980;
            final Widget left = Column(
              children: <Widget>[
                _WorkspaceCard(auth: auth),
                const SizedBox(height: AppSpacing.lg),
                const _AppearanceCard(),
                const SizedBox(height: AppSpacing.lg),
                const _SignOutCard(),
              ],
            );
            const Widget right = Column(
              children: <Widget>[
                _CapabilitiesCard(),
                SizedBox(height: AppSpacing.lg),
                _ReadinessCard(),
              ],
            );
            if (stacked) {
              return Column(
                children: <Widget>[
                  left,
                  const SizedBox(height: AppSpacing.lg),
                  right,
                ],
              );
            }
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Expanded(flex: 3, child: left),
                const SizedBox(width: AppSpacing.lg),
                const Expanded(flex: 2, child: right),
              ],
            );
          },
        ),
        const SizedBox(height: AppSpacing.md),
        Text(
          'Model API keys are held server-side only. The browser never receives a provider key.',
          style: AppType.caption.copyWith(color: p.textTertiary),
        ),
      ],
    );
  }
}

class _WorkspaceCard extends StatelessWidget {
  const _WorkspaceCard({required this.auth});

  final AuthState auth;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final AuthSession? s = auth.session;
    return AppCard(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const SectionHeader(
              title: 'Workspace',
              description: 'Identity used for every API call.'),
          DetailRow(label: 'Name', value: s?.organizationName ?? '—'),
          DetailRow(
              label: 'Organization ID',
              value: s?.organizationId ?? '—',
              mono: true),
          DetailRow(label: 'Your role', value: (s?.role ?? '—').toUpperCase()),
          DetailRow(
              label: 'Signed in as', value: s?.user.email ?? '—', mono: true),
          const SizedBox(height: AppSpacing.sm),
          Row(
            children: <Widget>[
              Icon(Icons.lock_outline, size: 14, color: p.textTertiary),
              const SizedBox(width: AppSpacing.xs),
              Expanded(
                child: Text(
                  'Every request carries an X-Organization-Id header; the server scopes all data to that tenant.',
                  style: AppType.caption.copyWith(color: p.textTertiary),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _AppearanceCard extends ConsumerWidget {
  const _AppearanceCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ThemeMode mode = ref.watch(themeModeProvider);
    return AppCard(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const SectionHeader(
              title: 'Appearance',
              description:
                  'Applies immediately and is remembered for this session.'),
          SegmentedButton<ThemeMode>(
            segments: const <ButtonSegment<ThemeMode>>[
              ButtonSegment<ThemeMode>(
                value: ThemeMode.light,
                label: Text('Light'),
                icon: Icon(Icons.light_mode_outlined, size: 16),
              ),
              ButtonSegment<ThemeMode>(
                value: ThemeMode.dark,
                label: Text('Dark'),
                icon: Icon(Icons.dark_mode_outlined, size: 16),
              ),
              ButtonSegment<ThemeMode>(
                value: ThemeMode.system,
                label: Text('System'),
                icon: Icon(Icons.brightness_auto_outlined, size: 16),
              ),
            ],
            selected: <ThemeMode>{mode},
            showSelectedIcon: false,
            onSelectionChanged: (Set<ThemeMode> selection) =>
                ref.read(themeModeProvider.notifier).state = selection.first,
          ),
        ],
      ),
    );
  }
}

class _CapabilitiesCard extends ConsumerWidget {
  const _CapabilitiesCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AppPalette p = context.palette;
    final AsyncValue<CapabilityMatrix> caps =
        ref.watch(telephonyCapabilitiesProvider);

    return AppCard(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const SectionHeader(
            title: 'Telephony provider',
            description:
                'What the active provider can actually do on your hardware.',
          ),
          AsyncView<CapabilityMatrix>(
            value: caps,
            onRetry: () => ref.invalidate(telephonyCapabilitiesProvider),
            skeletonLines: 6,
            isEmpty: (CapabilityMatrix _) => false,
            builder: (CapabilityMatrix c) => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Text('Active provider',
                        style: AppType.body.copyWith(color: p.textSecondary)),
                    const Spacer(),
                    AppBadge(label: c.provider, tone: AppBadgeTone.accent),
                  ],
                ),
                const SizedBox(height: AppSpacing.sm),
                for (final MapEntry<String, String> e in c.capabilities.entries)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 3),
                    child: Row(
                      children: <Widget>[
                        Expanded(
                          child: Text(
                            e.key
                                .split('_')
                                .map((String w) => w.isEmpty
                                    ? w
                                    : '${w[0].toUpperCase()}${w.substring(1)}')
                                .join(' '),
                            style:
                                AppType.body.copyWith(color: p.textSecondary),
                          ),
                        ),
                        AppBadge(
                          label: e.value,
                          tone: switch (e.value) {
                            'supported' => AppBadgeTone.success,
                            'unsupported' => AppBadgeTone.danger,
                            _ => AppBadgeTone.neutral,
                          },
                        ),
                      ],
                    ),
                  ),
                if (c.notes.isNotEmpty) ...<Widget>[
                  const SizedBox(height: AppSpacing.sm),
                  for (final String note in c.notes)
                    Padding(
                      padding: const EdgeInsets.only(bottom: AppSpacing.xxs),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Icon(Icons.info_outline,
                              size: 13, color: p.textTertiary),
                          const SizedBox(width: AppSpacing.xxs),
                          Expanded(
                              child: Text(note,
                                  style: AppType.caption
                                      .copyWith(color: p.textTertiary))),
                        ],
                      ),
                    ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Readiness is intentionally rendered from the raw check map. A 503 means the
/// platform is *not* ready, and we show which checks failed instead of a generic
/// error — honesty over polish.
class _ReadinessCard extends ConsumerStatefulWidget {
  const _ReadinessCard();

  @override
  ConsumerState<_ReadinessCard> createState() => _ReadinessCardState();
}

class _ReadinessCardState extends ConsumerState<_ReadinessCard> {
  bool _loading = true;
  Map<String, dynamic>? _checks;
  String? _notReady;
  Object? _error;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
      _checks = null;
      _notReady = null;
    });
    try {
      final Map<String, dynamic> body =
          await ref.read(healthRepositoryProvider).ready();
      if (!mounted) return;
      setState(() {
        _checks = body.mapOr('checks');
        if (body.str('status') != 'ready') {
          _notReady = 'The platform reported "${body.str('status')}".';
        }
      });
    } catch (e) {
      if (!mounted) return;
      // A 503 still carries the individual checks; surface them.
      if (e is ServerError &&
          e.statusCode == 503 &&
          e.details is Map<dynamic, dynamic>) {
        setState(() {
          _checks = (e.details! as Map<dynamic, dynamic>)
              .cast<String, dynamic>()
              .mapOr('checks');
          _notReady = 'One or more readiness checks failed.';
        });
      } else {
        setState(() => _error = e);
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;

    return AppCard(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          SectionHeader(
            title: 'Platform readiness',
            description: 'Live probes, not assumptions.',
            action: AppIconButton(
              icon: Icons.refresh,
              onPressed: _load,
              semanticLabel: 'Re-run readiness checks',
              tooltip: 'Re-run checks',
            ),
          ),
          if (_loading)
            const AppSkeleton(lines: 5)
          else if (_error != null)
            InlineError(error: _error!, onRetry: _load)
          else ...<Widget>[
            if (_notReady != null) ...<Widget>[
              InlineNotice(tone: NoticeTone.warning, message: _notReady!),
              const SizedBox(height: AppSpacing.sm),
            ],
            if (_checks == null || _checks!.isEmpty)
              Text('No checks were returned by the server.',
                  style: AppType.body.copyWith(color: p.textSecondary))
            else
              for (final MapEntry<String, dynamic> e in _checks!.entries)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 3),
                  child: Row(
                    children: <Widget>[
                      Expanded(
                        child: Text(
                          e.key
                              .split('_')
                              .map((String w) => w.isEmpty
                                  ? w
                                  : '${w[0].toUpperCase()}${w.substring(1)}')
                              .join(' '),
                          style: AppType.body.copyWith(color: p.textSecondary),
                        ),
                      ),
                      Text(
                        '${e.value}',
                        style: AppType.mono
                            .copyWith(color: _toneFor('${e.value}', p)),
                      ),
                    ],
                  ),
                ),
          ],
        ],
      ),
    );
  }

  static Color _toneFor(String value, AppPalette p) {
    final String v = value.toLowerCase();
    if (v.contains('connect') ||
        v == 'yes' ||
        v == 'healthy' ||
        v == 'configured') {
      return p.success;
    }
    if (v.contains('no') ||
        v.contains('error') ||
        v.contains('unhealthy') ||
        v.contains('offline')) {
      return p.danger;
    }
    if (v.contains('unknown') || v.contains('simulation')) return p.warning;
    return p.textPrimary;
  }
}

class _SignOutCard extends ConsumerWidget {
  const _SignOutCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AppCard(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const SectionHeader(
            title: 'Session',
            description:
                'Signing out clears the stored token from this browser.',
          ),
          AppButton(
            label: 'Sign out',
            variant: AppButtonVariant.danger,
            icon: Icons.logout,
            onPressed: () => ref.read(authProvider.notifier).logout(),
          ),
        ],
      ),
    );
  }
}
