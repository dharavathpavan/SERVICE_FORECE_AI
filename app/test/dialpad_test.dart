import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:serviceforce/src/theme/app_theme.dart';
import 'package:serviceforce/src/widgets/dialpad.dart';

/// The keypad only reports the character to append; the host field owns the
/// number. These tests pin that contract, including the long-press for `+`.
void main() {
  Future<void> pumpDialpad(
    WidgetTester tester,
    ValueChanged<String> onKey, {
    bool enabled = true,
  }) {
    return tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light(),
        home: Scaffold(body: Dialpad(onKey: onKey, enabled: enabled)),
      ),
    );
  }

  testWidgets('tapping a key reports that digit', (WidgetTester tester) async {
    final List<String> pressed = <String>[];
    await pumpDialpad(tester, pressed.add);

    await tester.tap(find.text('2'));
    await tester.tap(find.text('#'));
    await tester.pump();

    expect(pressed, <String>['2', '#']);
  });

  testWidgets('long-pressing 0 inserts the international prefix',
      (WidgetTester tester) async {
    final List<String> pressed = <String>[];
    await pumpDialpad(tester, pressed.add);

    await tester.longPress(find.text('0'));
    await tester.pump();

    expect(pressed, <String>['+']);
  });

  testWidgets('a disabled keypad reports nothing', (WidgetTester tester) async {
    final List<String> pressed = <String>[];
    await pumpDialpad(tester, pressed.add, enabled: false);

    await tester.tap(find.text('5'));
    await tester.pump();

    expect(pressed, isEmpty);
  });
}
