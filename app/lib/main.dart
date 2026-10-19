import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'src/app.dart';
import 'src/state/providers.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // The persisted session is restored *before* the first frame on purpose: the
  // router reads the browser URL when it first mounts, so mounting it later (as
  // an after-frame async task) makes Flutter overwrite a deep link - or a plain
  // reload - with the default route. Restoring up front keeps the URL
  // authoritative from the very first frame.
  final ProviderContainer container = ProviderContainer();
  await container.read(authProvider.notifier).restore();

  runApp(
    UncontrolledProviderScope(
      container: container,
      child: const ServiceForceApp(),
    ),
  );
}
