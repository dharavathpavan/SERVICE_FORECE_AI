import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../api/models.dart';
import '../state/providers.dart';
import '../theme/tokens.dart';
import 'primitives.dart';

class NavItem {
  const NavItem(
      {required this.label,
      required this.icon,
      required this.route,
      this.adminOnly = false});

  final String label;
  final IconData icon;
  final String route;
  final bool adminOnly;
}

class NavGroup {
  const NavGroup({required this.title, required this.items});

  final String title;
  final List<NavItem> items;
}

const List<NavGroup> kNavGroups = <NavGroup>[
  NavGroup(
    title: 'Workspace',
    items: <NavItem>[
      NavItem(
          label: 'Dashboard', icon: Icons.dashboard_outlined, route: '/app'),
      NavItem(label: 'Calls', icon: Icons.call_outlined, route: '/app/calls'),
      NavItem(
          label: 'Agents',
          icon: Icons.smart_toy_outlined,
          route: '/app/agents'),
      NavItem(
          label: 'Knowledge',
          icon: Icons.menu_book_outlined,
          route: '/app/knowledge'),
    ],
  ),
  NavGroup(
    title: 'Telephony',
    items: <NavItem>[
      NavItem(
          label: 'Phone lines',
          icon: Icons.phone_in_talk_outlined,
          route: '/app/phone-lines'),
      NavItem(
          label: 'Gateways',
          icon: Icons.router_outlined,
          route: '/app/gateways'),
    ],
  ),
  NavGroup(
    title: 'Outreach',
    items: <NavItem>[
      NavItem(
          label: 'Campaigns',
          icon: Icons.campaign_outlined,
          route: '/app/campaigns'),
      NavItem(
          label: 'Contacts',
          icon: Icons.contacts_outlined,
          route: '/app/contacts'),
    ],
  ),
  NavGroup(
    title: 'Insights',
    items: <NavItem>[
      NavItem(
          label: 'Analytics',
          icon: Icons.insights_outlined,
          route: '/app/analytics'),
      NavItem(
          label: 'Audit log',
          icon: Icons.receipt_long_outlined,
          route: '/app/audit',
          adminOnly: true),
    ],
  ),
  NavGroup(
    title: 'Administration',
    items: <NavItem>[
      NavItem(label: 'Team', icon: Icons.groups_outlined, route: '/app/team'),
      NavItem(
          label: 'Settings',
          icon: Icons.settings_outlined,
          route: '/app/settings'),
    ],
  ),
];

/// Desktop-first application shell: persistent sidebar, sticky top bar, scrollable content.
class AppShell extends ConsumerStatefulWidget {
  const AppShell({super.key, required this.child, required this.location});

  final Widget child;
  final String location;

  @override
  ConsumerState<AppShell> createState() => _AppShellState();
}

class _AppShellState extends ConsumerState<AppShell> {
  bool _collapsed = false;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final double width = MediaQuery.sizeOf(context).width;
    final bool narrow = width < 760;
    final bool effectiveCollapsed = _collapsed || width < 760;

    // Mobile: bottom navigation bar per PRD §4 (Home, Agents, Calls, Contacts, Settings).
    if (narrow) {
      return Scaffold(
        backgroundColor: p.background,
        body: Column(
          children: <Widget>[
            _TopBar(onMenu: null),
            Divider(height: 1, color: p.outline),
            Expanded(
              child: SelectionArea(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  child: widget.child,
                ),
              ),
            ),
          ],
        ),
        bottomNavigationBar: _MobileBottomNav(location: widget.location),
      );
    }

    return Scaffold(
      backgroundColor: p.background,
      body: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          _Sidebar(
            collapsed: effectiveCollapsed,
            location: widget.location,
            onToggle: () => setState(() => _collapsed = !_collapsed),
            showToggle: !narrow,
          ),
          VerticalDivider(width: 1, color: p.outline),
          Expanded(
            child: Column(
              children: <Widget>[
                _TopBar(
                    onMenu: width < 760 ? () => _showMobileNav(context) : null),
                Divider(height: 1, color: p.outline),
                Expanded(
                  child: SelectionArea(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.all(AppSpacing.lg),
                      child: Align(
                        alignment: Alignment.topCenter,
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 1240),
                          child: widget.child,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _showMobileNav(BuildContext context) {
    final AppPalette p = context.palette;
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: p.surface,
      builder: (BuildContext context) => SafeArea(
        child: SingleChildScrollView(
          child: Column(
            children: <Widget>[
              for (final NavGroup g in kNavGroups) ...<Widget>[
                Padding(
                  padding: const EdgeInsets.fromLTRB(AppSpacing.md,
                      AppSpacing.md, AppSpacing.md, AppSpacing.xxs),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: Text(g.title.toUpperCase(),
                        style: AppType.micro.copyWith(color: p.textTertiary)),
                  ),
                ),
                for (final NavItem item in g.items)
                  ListTile(
                    leading: Icon(item.icon, size: 18, color: p.textSecondary),
                    title: Text(item.label,
                        style: AppType.body.copyWith(color: p.textPrimary)),
                    onTap: () {
                      Navigator.of(context).pop();
                      context.go(item.route);
                    },
                  ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Mobile bottom navigation per PRD §4: Home, Agents, Calls, Contacts, Settings.
class _MobileBottomNav extends StatelessWidget {
  const _MobileBottomNav({required this.location});

  final String location;

  static const List<_MobileNavItem> _items = <_MobileNavItem>[
    _MobileNavItem('Home', Icons.dashboard_outlined, '/app'),
    _MobileNavItem('Agents', Icons.smart_toy_outlined, '/app/agents'),
    _MobileNavItem('Calls', Icons.call_outlined, '/app/calls'),
    _MobileNavItem('Contacts', Icons.contacts_outlined, '/app/contacts'),
    _MobileNavItem('Settings', Icons.settings_outlined, '/app/settings'),
  ];

  int get _selectedIndex {
    if (location.startsWith('/app/agents')) return 1;
    if (location.startsWith('/app/calls')) return 2;
    if (location.startsWith('/app/contacts')) return 3;
    if (location.startsWith('/app/settings')) return 4;
    return 0;
  }

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    return NavigationBar(
      selectedIndex: _selectedIndex,
      onDestinationSelected: (int i) => context.go(_items[i].route),
      backgroundColor: p.surface,
      indicatorColor: p.accent.withValues(alpha: 0.15),
      destinations: <NavigationDestination>[
        for (final _MobileNavItem item in _items)
          NavigationDestination(
            icon: Icon(item.icon, color: p.textSecondary),
            selectedIcon: Icon(item.icon, color: p.accent),
            label: item.label,
          ),
      ],
    );
  }
}

class _MobileNavItem {
  const _MobileNavItem(this.label, this.icon, this.route);
  final String label;
  final IconData icon;
  final String route;
}

class _Sidebar extends ConsumerWidget {
  const _Sidebar({
    required this.collapsed,
    required this.location,
    required this.onToggle,
    required this.showToggle,
  });

  final bool collapsed;
  final String location;
  final VoidCallback onToggle;
  final bool showToggle;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AppPalette p = context.palette;
    final String role = ref.watch(authProvider).session?.role ?? 'operator';
    final bool isAdmin = role == 'owner' || role == 'admin';

    return AnimatedContainer(
      duration: AppDurations.normal,
      curve: AppDurations.ease,
      width: collapsed ? 64 : 236,
      color: p.surface,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          SizedBox(
            height: 60,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
              child: Row(
                children: <Widget>[
                  Container(
                    width: 28,
                    height: 28,
                    decoration: BoxDecoration(
                        color: p.accent, borderRadius: AppRadii.allSm),
                    alignment: Alignment.center,
                    child: Icon(Icons.graphic_eq, size: 16, color: p.onAccent),
                  ),
                  if (!collapsed) ...<Widget>[
                    const SizedBox(width: AppSpacing.xs),
                    Expanded(
                      child: Text('ServiceForce',
                          style:
                              AppType.subtitle.copyWith(color: p.textPrimary)),
                    ),
                  ],
                ],
              ),
            ),
          ),
          Divider(height: 1, color: p.outline),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
              children: <Widget>[
                for (final NavGroup g in kNavGroups) ...<Widget>[
                  if (!collapsed)
                    Padding(
                      padding: const EdgeInsets.fromLTRB(AppSpacing.md,
                          AppSpacing.sm, AppSpacing.md, AppSpacing.xxs),
                      child: Text(g.title.toUpperCase(),
                          style: AppType.micro.copyWith(color: p.textTertiary)),
                    )
                  else
                    const SizedBox(height: AppSpacing.sm),
                  for (final NavItem item in g.items)
                    if (!item.adminOnly || isAdmin)
                      _NavRow(
                          item: item,
                          selected: _isSelected(item.route),
                          collapsed: collapsed),
                ],
              ],
            ),
          ),
          Divider(height: 1, color: p.outline),
          if (showToggle)
            Align(
              alignment: collapsed ? Alignment.center : Alignment.centerRight,
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.xxs),
                child: AppIconButton(
                  icon: collapsed ? Icons.chevron_right : Icons.chevron_left,
                  onPressed: onToggle,
                  semanticLabel:
                      collapsed ? 'Expand navigation' : 'Collapse navigation',
                  tooltip: collapsed ? 'Expand' : 'Collapse',
                ),
              ),
            ),
        ],
      ),
    );
  }

  bool _isSelected(String route) {
    if (route == '/app') return location == '/app' || location == '/app/';
    return location.startsWith(route);
  }
}

class _NavRow extends StatelessWidget {
  const _NavRow(
      {required this.item, required this.selected, required this.collapsed});

  final NavItem item;
  final bool selected;
  final bool collapsed;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final Widget row = Container(
      height: 36,
      padding: EdgeInsets.symmetric(horizontal: collapsed ? 0 : AppSpacing.sm),
      decoration: BoxDecoration(
        color: selected ? p.infoSurface : Colors.transparent,
        borderRadius: AppRadii.allSm,
        border: Border.all(
            color: selected
                ? p.accent.withValues(alpha: 0.35)
                : Colors.transparent),
      ),
      child: Row(
        mainAxisAlignment:
            collapsed ? MainAxisAlignment.center : MainAxisAlignment.start,
        children: <Widget>[
          Icon(item.icon,
              size: 17, color: selected ? p.accent : p.textSecondary),
          if (!collapsed) ...<Widget>[
            const SizedBox(width: AppSpacing.xs),
            Expanded(
              child: Text(
                item.label,
                style: AppType.body.copyWith(
                  color: selected ? p.accent : p.textPrimary,
                  fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
                ),
              ),
            ),
          ],
        ],
      ),
    );

    return Padding(
      padding:
          const EdgeInsets.symmetric(horizontal: AppSpacing.xs, vertical: 1),
      child: Material(
        color: Colors.transparent,
        borderRadius: AppRadii.allSm,
        child: InkWell(
          onTap: () => context.go(item.route),
          borderRadius: AppRadii.allSm,
          hoverColor: p.surfaceVariant,
          focusColor: p.focusRing.withValues(alpha: 0.25),
          child: Tooltip(
            message: collapsed ? item.label : '',
            child: row,
          ),
        ),
      ),
    );
  }
}

class _TopBar extends ConsumerWidget {
  const _TopBar({this.onMenu});

  final VoidCallback? onMenu;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AppPalette p = context.palette;
    final AuthState auth = ref.watch(authProvider);
    final String orgName = auth.session?.organizationName ?? 'Workspace';

    return Container(
      height: 60,
      color: p.surface,
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
      child: Row(
        children: <Widget>[
          if (onMenu != null)
            AppIconButton(
                icon: Icons.menu,
                onPressed: onMenu,
                semanticLabel: 'Open navigation'),
          if (onMenu != null) const SizedBox(width: AppSpacing.xs),
          Icon(Icons.business_outlined, size: 16, color: p.textTertiary),
          const SizedBox(width: AppSpacing.xs),
          Text(orgName,
              style: AppType.bodyStrong.copyWith(color: p.textPrimary)),
          const Spacer(),
          const _ProviderStatusChip(),
          const SizedBox(width: AppSpacing.sm),
          PopupMenuButton<String>(
            tooltip: 'Account',
            position: PopupMenuPosition.under,
            color: p.surface,
            onSelected: (String value) async {
              if (value == 'logout') {
                await ref.read(authProvider.notifier).logout();
              } else if (value == 'settings') {
                context.go('/app/settings');
              }
            },
            itemBuilder: (BuildContext context) => <PopupMenuEntry<String>>[
              PopupMenuItem<String>(
                enabled: false,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(auth.session?.user.fullName ?? 'User',
                        style:
                            AppType.bodyStrong.copyWith(color: p.textPrimary)),
                    Text(auth.session?.user.email ?? '',
                        style:
                            AppType.caption.copyWith(color: p.textSecondary)),
                  ],
                ),
              ),
              const PopupMenuDivider(),
              const PopupMenuItem<String>(
                  value: 'settings', child: Text('Workspace settings')),
              const PopupMenuItem<String>(
                  value: 'logout', child: Text('Sign out')),
            ],
            child: Row(
              children: <Widget>[
                CircleAvatar(
                  radius: 14,
                  backgroundColor: p.surfaceVariant,
                  child: Text(
                    _initials(auth.session?.user.fullName ?? 'U'),
                    style: AppType.caption.copyWith(
                        color: p.textPrimary, fontWeight: FontWeight.w600),
                  ),
                ),
                const SizedBox(width: AppSpacing.xs),
                Icon(Icons.expand_more, size: 16, color: p.textTertiary),
              ],
            ),
          ),
        ],
      ),
    );
  }

  static String _initials(String name) {
    final List<String> parts = name.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty || parts.first.isEmpty) return 'U';
    if (parts.length == 1) return parts.first.substring(0, 1).toUpperCase();
    return (parts.first.substring(0, 1) + parts.last.substring(0, 1))
        .toUpperCase();
  }
}

/// Shows the configured telephony provider and whether the gateway is reachable.
/// Honest by construction: it reports "not verified" rather than assuming health.
class _ProviderStatusChip extends ConsumerWidget {
  const _ProviderStatusChip();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<CapabilityMatrix> caps =
        ref.watch(telephonyCapabilitiesProvider);
    return caps.when(
      loading: () => const AppBadge(
          label: 'Checking provider', tone: AppBadgeTone.neutral),
      error: (Object _, StackTrace __) => const AppBadge(
        label: 'Provider unknown',
        tone: AppBadgeTone.warning,
        icon: Icons.help_outline,
      ),
      data: (CapabilityMatrix c) => AppBadge(
        label: 'Provider: ${c.provider}',
        tone: AppBadgeTone.neutral,
        icon: Icons.router_outlined,
      ),
    );
  }
}
