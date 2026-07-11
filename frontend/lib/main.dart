import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/theme/app_theme.dart';
import 'services/api_service.dart';
import 'services/auth_service.dart';
import 'ui/screens/auth/auth_wrapper.dart';
import 'ui/screens/url_helper.dart';

final navigatorKey = GlobalKey<NavigatorState>();

void main() {
  final initialTab = getHashEarly();

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthService>(create: (_) => AuthService()),
        ProxyProvider<AuthService, ApiService>(
          update: (_, auth, _) => ApiService(auth),
        ),
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
