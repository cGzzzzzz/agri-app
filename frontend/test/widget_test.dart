import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/main.dart';
import 'package:frontend/models/onboarding_data.dart';
import 'package:frontend/services/api_service.dart';
import 'package:frontend/services/auth_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('AgriAI app starts with loading indicator', (WidgetTester tester) async {
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<AuthService>(create: (_) => AuthService()),
          ProxyProvider<AuthService, ApiService>(
            update: (_, auth, __) => ApiService(auth),
          ),
          ChangeNotifierProvider<OnboardingData>(create: (_) => OnboardingData()),
        ],
        child: const AgriAIApp(),
      ),
    );
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });
}
