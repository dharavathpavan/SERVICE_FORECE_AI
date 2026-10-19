import 'package:flutter/material.dart';

import '../theme/tokens.dart';

/// One key on the handset.
class _DialKey {
  const _DialKey(this.digit, {this.letters, this.longPress});

  final String digit;

  /// Letters printed under the digit on a real handset (`ABC`, `DEF`, ...).
  final String? letters;

  /// Character inserted on a long press: `0` long-presses to `+`.
  final String? longPress;
}

/// A touch keypad for composing a destination number.
///
/// Laid out like a telephone handset so muscle memory works, and long-pressing
/// `0` inserts the international `+` prefix. Pair it with an editable field and
/// physical keyboards keep working; the keypad only appends characters.
class Dialpad extends StatelessWidget {
  const Dialpad({super.key, required this.onKey, this.enabled = true});

  /// Called with the character to append: `0-9`, `*`, `#` or `+`.
  final ValueChanged<String> onKey;

  /// Set to false while a call is being placed.
  final bool enabled;

  static const List<_DialKey> _keys = <_DialKey>[
    _DialKey('1'),
    _DialKey('2', letters: 'ABC'),
    _DialKey('3', letters: 'DEF'),
    _DialKey('4', letters: 'GHI'),
    _DialKey('5', letters: 'JKL'),
    _DialKey('6', letters: 'MNO'),
    _DialKey('7', letters: 'PQRS'),
    _DialKey('8', letters: 'TUV'),
    _DialKey('9', letters: 'WXYZ'),
    _DialKey('*'),
    _DialKey('0', letters: '+', longPress: '+'),
    _DialKey('#'),
  ];

  @override
  Widget build(BuildContext context) {
    return GridView.count(
      crossAxisCount: 3,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: AppSpacing.xs,
      crossAxisSpacing: AppSpacing.xs,
      childAspectRatio: 2,
      children: <Widget>[
        for (final _DialKey dialKey in _keys)
          _DialKeyButton(dialKey: dialKey, enabled: enabled, onKey: onKey),
      ],
    );
  }
}

class _DialKeyButton extends StatelessWidget {
  const _DialKeyButton({
    required this.dialKey,
    required this.enabled,
    required this.onKey,
  });

  final _DialKey dialKey;
  final bool enabled;
  final ValueChanged<String> onKey;

  @override
  Widget build(BuildContext context) {
    final AppPalette p = context.palette;
    final bool longPressable = dialKey.longPress != null;

    return Semantics(
      button: true,
      enabled: enabled,
      label: longPressable
          ? 'Key ${dialKey.digit}, long press for ${dialKey.longPress}'
          : 'Key ${dialKey.digit}',
      excludeSemantics: true,
      child: Material(
        color: p.surfaceVariant,
        borderRadius: AppRadii.allSm,
        child: InkWell(
          borderRadius: AppRadii.allSm,
          onTap: enabled ? () => onKey(dialKey.digit) : null,
          onLongPress:
              enabled && longPressable ? () => onKey(dialKey.longPress!) : null,
          child: Container(
            decoration: BoxDecoration(
              borderRadius: AppRadii.allSm,
              border: Border.all(color: p.outline),
            ),
            alignment: Alignment.center,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: <Widget>[
                Text(
                  dialKey.digit,
                  style: AppType.title.copyWith(
                    color: enabled ? p.textPrimary : p.textTertiary,
                  ),
                ),
                if (dialKey.letters != null)
                  Text(
                    dialKey.letters!,
                    style: AppType.micro.copyWith(
                      color: p.textTertiary,
                      letterSpacing: 1.2,
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
