import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../api/api_error.dart';
import '../../state/providers.dart';
import '../../theme/tokens.dart';
import '../../widgets/async_view.dart';
import '../../widgets/inputs.dart';
import '../../widgets/primitives.dart';
import 'auth_shell.dart';

class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key});

  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage> {
  final TextEditingController _email = TextEditingController();
  final TextEditingController _password = TextEditingController();
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    final bool ok = await ref
        .read(authProvider.notifier)
        .login(_email.text, _password.text);
    if (!mounted) return;
    if (ok) context.go('/app');
  }

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final AuthState auth = ref.watch(authProvider);
    final ApiError? error =
        auth.error is ApiError ? auth.error! as ApiError : null;

    return AuthShell(
      title: 'Sign in',
      subtitle: 'Welcome back. Enter your credentials to continue.',
      form: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            if (auth.error != null) ...<Widget>[
              InlineError(error: auth.error!),
              const SizedBox(height: AppSpacing.md),
            ],
            AppTextField(
              label: 'Work email',
              controller: _email,
              hint: 'you@company.com',
              keyboardType: TextInputType.emailAddress,
              prefixIcon: Icons.mail_outline,
              autofillHints: const <String>[AutofillHints.username],
              textInputAction: TextInputAction.next,
            ),
            const SizedBox(height: AppSpacing.sm),
            AppTextField(
              label: 'Password',
              controller: _password,
              hint: '••••••••',
              obscure: true,
              prefixIcon: Icons.lock_outline,
              autofillHints: const <String>[AutofillHints.password],
              textInputAction: TextInputAction.done,
              onSubmitted: (_) => _submit(),
            ),
            const SizedBox(height: AppSpacing.md),
            AppButton(
              label: 'Sign in',
              expand: true,
              loading: auth.busy,
              onPressed: auth.busy ? null : _submit,
            ),
            if (error is NetworkError) ...<Widget>[
              const SizedBox(height: AppSpacing.sm),
              Text(
                'Tip: start the backend with "uvicorn app.main:app --reload" and confirm the API URL.',
                style: AppType.caption.copyWith(color: p.textTertiary),
              ),
            ],
          ],
        ),
      ),
      footer: Row(
        children: <Widget>[
          Text('New to ServiceForce?',
              style: AppType.body.copyWith(color: p.textSecondary)),
          TextButton(
            onPressed: () => context.go('/signup'),
            child: const Text('Create an account'),
          ),
        ],
      ),
    );
  }
}
