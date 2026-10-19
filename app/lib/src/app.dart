import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'router/app_router.dart';
import 'state/providers.dart';
import 'theme/app_theme.dart';

class ServiceForceApp extends ConsumerWidget {
  const ServiceForceApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ThemeMode mode = ref.watch(themeModeProvider);
    final GoRouter router = ref.watch(routerProvider);

    // Always the router variant: the session was already restored in `main`, and
    // swapping in a plain `MaterialApp` would discard the browser URL the router
    // had just resolved.
    return MaterialApp.router(
      title: 'ServiceForce.ai',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: mode,
      routerConfig: router,
    );
  }
}
