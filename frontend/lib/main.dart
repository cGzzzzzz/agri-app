import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/theme/app_theme.dart';
import 'models/onboarding_data.dart';
import 'services/api_service.dart';
import 'services/auth_service.dart';
import 'ui/screens/auth/auth_wrapper.dart';
import 'ui/screens/url_helper.dart';

final navigatorKey = GlobalKey<NavigatorState>();

void main() {
  final initialTab = getHashEarly();

  ErrorWidget.builder = (FlutterErrorDetails details) {
    if (kReleaseMode) {
      return const Center(
        child: Text('Something went wrong. Please restart the app.',
            style: TextStyle(fontSize: 16)),
      );
    }
    return Center(
      child: Text(details.exceptionAsString(),
          style: const TextStyle(fontSize: 12, fontFamily: 'monospace')),
    );
  };

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthService>(create: (_) => AuthService()),
        ProxyProvider<AuthService, ApiService>(
          update: (_, auth, __) => ApiService(auth),
        ),
        ChangeNotifierProvider<OnboardingData>(create: (_) => OnboardingData()),
      ],
      child: AgriAIApp(initialTab: initialTab),
    ),
  );
}

class AgriAIApp extends StatelessWidget {
  final String initialTab;
  const AgriAIApp({super.key, this.initialTab = ''});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AgriAI',
      debugShowCheckedModeBanner: false,
      navigatorKey: navigatorKey,
      theme: AppTheme.lightTheme,
      home: AuthWrapper(initialTab: initialTab),
    );
  }
}
