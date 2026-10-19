import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/agents/agent_detail_page.dart';
import '../features/agents/agents_page.dart';
import '../features/analytics/analytics_page.dart';
import '../features/audit/audit_page.dart';
import '../features/auth/login_page.dart';
import '../features/auth/signup_page.dart';
import '../features/calls/call_detail_page.dart';
import '../features/calls/calls_page.dart';
import '../features/campaigns/campaigns_page.dart';
import '../features/contacts/contacts_page.dart';
import '../features/dashboard/dashboard_page.dart';
import '../features/gateways/gateways_page.dart';
import '../features/knowledge/knowledge_page.dart';
import '../features/marketing/features_page.dart';
import '../features/marketing/landing_page.dart';
import '../features/marketing/pricing_page.dart';
import '../features/phone_lines/phone_lines_page.dart';
import '../features/settings/settings_page.dart';
import '../features/team/team_page.dart';
import '../state/providers.dart';
import '../state/session_store.dart';
import '../widgets/app_shell.dart';

/// Public routes reachable without a session.
const Set<String> kPublicRoutes = <String>{
  '/',
  '/login',
  '/signup',
  '/features',
  '/pricing'
};

final Provider<GoRouter> routerProvider = Provider<GoRouter>((Ref ref) {
  final SessionStore store = ref.watch(sessionStoreProvider);

  return GoRouter(
    // Deliberately no `initialLocation`: on web the location must come from the
    // URL. A hardcoded default rewrites deep links - and a reload while signed
    // in - back to the landing page once the router reports its first value.
    // Session changes re-evaluate the redirect, so sign-in/out navigates cleanly.
    refreshListenable: store,
    redirect: (BuildContext context, GoRouterState state) {
      if (!store.ready) return null;

      final bool isPublic = kPublicRoutes.contains(state.matchedLocation);
      final bool authed = store.isAuthenticated;

      if (!authed && !isPublic) return '/login';
      if (authed &&
          (state.matchedLocation == '/login' ||
              state.matchedLocation == '/signup')) {
        return '/app';
      }
      return null;
    },
    routes: <RouteBase>[
      GoRoute(path: '/', builder: (_, GoRouterState s) => const LandingPage()),
      GoRoute(
          path: '/features',
          builder: (_, GoRouterState s) => const FeaturesPage()),
      GoRoute(
          path: '/pricing',
          builder: (_, GoRouterState s) => const PricingPage()),
      GoRoute(
          path: '/login', builder: (_, GoRouterState s) => const LoginPage()),
      GoRoute(
          path: '/signup', builder: (_, GoRouterState s) => const SignupPage()),
      ShellRoute(
        builder: (BuildContext context, GoRouterState state, Widget child) =>
            AppShell(location: state.matchedLocation, child: child),
        routes: <RouteBase>[
          GoRoute(
              path: '/app',
              builder: (_, GoRouterState s) => const DashboardPage()),
          GoRoute(
              path: '/app/calls',
              builder: (_, GoRouterState s) => const CallsPage()),
          GoRoute(
            path: '/app/calls/:id',
            builder: (_, GoRouterState s) =>
                CallDetailPage(callId: s.pathParameters['id']!),
          ),
          GoRoute(
              path: '/app/agents',
              builder: (_, GoRouterState s) => const AgentsPage()),
          GoRoute(
            path: '/app/agents/:id',
            builder: (_, GoRouterState s) =>
                AgentDetailPage(agentId: s.pathParameters['id']!),
          ),
          GoRoute(
              path: '/app/knowledge',
              builder: (_, GoRouterState s) => const KnowledgePage()),
          GoRoute(
              path: '/app/phone-lines',
              builder: (_, GoRouterState s) => const PhoneLinesPage()),
          GoRoute(
              path: '/app/gateways',
              builder: (_, GoRouterState s) => const GatewaysPage()),
          GoRoute(
              path: '/app/campaigns',
              builder: (_, GoRouterState s) => const CampaignsPage()),
          GoRoute(
              path: '/app/contacts',
              builder: (_, GoRouterState s) => const ContactsPage()),
          GoRoute(
              path: '/app/analytics',
              builder: (_, GoRouterState s) => const AnalyticsPage()),
          GoRoute(
              path: '/app/audit',
              builder: (_, GoRouterState s) => const AuditPage()),
          GoRoute(
              path: '/app/team',
              builder: (_, GoRouterState s) => const TeamPage()),
          GoRoute(
              path: '/app/settings',
              builder: (_, GoRouterState s) => const SettingsPage()),
        ],
      ),
    ],
  );
});
