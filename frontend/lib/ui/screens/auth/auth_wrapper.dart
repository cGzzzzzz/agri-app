import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../services/api_service.dart';
import '../../../services/auth_service.dart';
import '../main_navigation.dart';
import 'login_screen.dart';

class AuthWrapper extends StatefulWidget {
  final String initialTab;
  const AuthWrapper({super.key, this.initialTab = ''});

  @override
  State<AuthWrapper> createState() => _AuthWrapperState();
}

class _AuthWrapperState extends State<AuthWrapper> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _initAuth();
    });
  }

  Future<void> _initAuth() async {
    final auth = Provider.of<AuthService>(context, listen: false);
    await auth.init();

    // If we have a token, verify it's still valid by calling /auth/me
    if (auth.isAuthenticated) {
      final api = ApiService(auth);
      final profile = await api.getProfile();
      if (profile == null) {
        // Token invalid/expired - logout and show login
        await auth.logout();
        if (mounted) setState(() {});
        return;
      }
    }

    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthService>(context);

    if (!auth.isInitialized) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    if (auth.isAuthenticated) {
      return MainNavigation(initialTab: widget.initialTab);
    }

    return const LoginScreen();
  }
}
