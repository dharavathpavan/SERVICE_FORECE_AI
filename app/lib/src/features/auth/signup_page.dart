import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../state/providers.dart';
import '../../theme/tokens.dart';
import '../../widgets/async_view.dart';
import '../../widgets/inputs.dart';
import '../../widgets/primitives.dart';
import 'auth_shell.dart';

class SignupPage extends ConsumerStatefulWidget {
  const SignupPage({super.key});

  @override
  ConsumerState<SignupPage> createState() => _SignupPageState();
}

class _SignupPageState extends ConsumerState<SignupPage> {
  final TextEditingController _org = TextEditingController();
  final TextEditingController _name = TextEditingController();
  final TextEditingController _email = TextEditingController();
  final TextEditingController _password = TextEditingController();

  String? _orgError;
  String? _nameError;
  String? _emailError;
  String? _passwordError;

  @override
  void dispose() {
    _org.dispose();
    _name.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  String? _requireValue(String? v, String field) {
    if (v == null || v.trim().isEmpty) return '$field is required.';
    return null;
  }

  String? _validateEmail(String? v) {
    final String? required = _requireValue(v, 'Email');
    if (required != null) return required;
    return RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(v!.trim())
        ? null
        : 'Enter a valid email address.';
  }

  String? _validatePassword(String? v) {
    if (v == null || v.isEmpty) return 'Password is required.';
    if (v.length < 8) return 'Use at least 8 characters.';
    if (!RegExp(r'[A-Za-z]').hasMatch(v) || !RegExp(r'[0-9]').hasMatch(v)) {
      return 'Include at least one letter and one number.';
    }
    return null;
  }

  bool _validate() {
    final String? org = _requireValue(_org.text, 'Workspace name');
    final String? name = _requireValue(_name.text, 'Name');
    final String? email = _validateEmail(_email.text);
    final String? password = _validatePassword(_password.text);
    setState(() {
      _orgError = org;
      _nameError = name;
      _emailError = email;
      _passwordError = password;
    });
    return org == null && name == null && email == null && password == null;
  }

  Future<void> _submit() async {
    if (!_validate()) return;
    final bool ok = await ref.read(authProvider.notifier).register(
          email: _email.text,
          fullName: _name.text,
          password: _password.text,
          organizationName: _org.text,
        );
    if (!mounted) return;
    if (ok) context.go('/app');
  }

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final AuthState auth = ref.watch(authProvider);

    return AuthShell(
      title: 'Create your workspace',
      subtitle: 'Set up your organisation and first agent access.',
      form: Form(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            if (auth.error != null) ...<Widget>[
              InlineError(error: auth.error!),
              const SizedBox(height: AppSpacing.md),
            ],
            AppTextField(
              label: 'Workspace name',
              controller: _org,
              hint: 'Acme Support',
              prefixIcon: Icons.business_outlined,
              helper: 'Shown across the dashboard. Can be changed later.',
              error: _orgError,
            ),
            const SizedBox(height: AppSpacing.sm),
            AppTextField(
              label: 'Your name',
              controller: _name,
              hint: 'Jordan Lee',
              prefixIcon: Icons.person_outline,
              autofillHints: const <String>[AutofillHints.name],
              error: _nameError,
            ),
            const SizedBox(height: AppSpacing.sm),
            AppTextField(
              label: 'Work email',
              controller: _email,
              hint: 'you@company.com',
              keyboardType: TextInputType.emailAddress,
              prefixIcon: Icons.mail_outline,
              autofillHints: const <String>[AutofillHints.email],
              error: _emailError,
            ),
            const SizedBox(height: AppSpacing.sm),
            AppTextField(
              label: 'Password',
              controller: _password,
              hint: 'At least 8 characters',
              obscure: true,
              prefixIcon: Icons.lock_outline,
              helper: 'Use at least one letter and one number.',
              error: _passwordError,
              onSubmitted: (_) => _submit(),
            ),
            const SizedBox(height: AppSpacing.md),
            AppButton(
              label: 'Create workspace',
              expand: true,
              loading: auth.busy,
              onPressed: auth.busy ? null : _submit,
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              'By creating a workspace you agree to place calls only to contacts you are '
              'permitted to call, and to honour opt-out requests.',
              style: AppType.caption.copyWith(color: p.textTertiary),
            ),
          ],
        ),
      ),
      footer: Row(
        children: <Widget>[
          Text('Already have an account?',
              style: AppType.body.copyWith(color: p.textSecondary)),
          TextButton(
            onPressed: () => context.go('/login'),
            child: const Text('Sign in'),
          ),
        ],
      ),
    );
  }
}
