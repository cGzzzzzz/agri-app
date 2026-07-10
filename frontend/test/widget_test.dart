// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/main.dart';

void main() {
  testWidgets('AgriAI app sanity test', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const AgriAIApp());

    // Verify that Splash Screen elements are rendered
    expect(find.text('AgriAI'), findsOneWidget);
    expect(find.text('Context-Aware Decision Intelligence'), findsOneWidget);

    // Wait for the 2-second splash screen timer and route transition
    await tester.pump(const Duration(seconds: 2));
    await tester.pumpAndSettle();

    // Verify that the app navigated to the Language Selection Screen
    expect(find.text('Select language'), findsOneWidget);
    expect(find.text('Tamil'), findsOneWidget);
  });
}
