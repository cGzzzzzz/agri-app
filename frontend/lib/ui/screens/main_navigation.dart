import 'package:flutter/material.dart';

import 'assistant/assistant_screen.dart';
import 'dashboard/dashboard_screen.dart';
import 'farm_screen.dart';
import 'profile_screen.dart';
import 'scan_screen.dart';
import 'url_helper.dart';

class MainNavigation extends StatefulWidget {
  final String initialTab;
  const MainNavigation({super.key, this.initialTab = ''});

  @override
  State<MainNavigation> createState() => _MainNavigationState();
}

class _MainNavigationState extends State<MainNavigation> {
  static const _tabNames = ['home', 'assistant', 'scan', 'farm', 'profile'];

  late int _currentIndex;

  final List<Widget> _screens = const [
    DashboardScreen(),
    AssistantScreen(),
    ScanScreen(),
    FarmScreen(),
    ProfileScreen(),
  ];

  @override
  void initState() {
    super.initState();
    final earlyHash = widget.initialTab;
    if (earlyHash.isNotEmpty && _tabNames.contains(earlyHash)) {
      _currentIndex = _tabNames.indexOf(earlyHash);
    } else {
      _currentIndex = 0;
    }
    listenHashChange(_onHashChanged);
  }

  void _onHashChanged(String hash) {
    if (!mounted) return;
    final index = _tabNames.indexOf(hash);
    if (index >= 0 && index != _currentIndex) {
      setState(() => _currentIndex = index);
    }
  }

  void _switchTab(int index) {
    setState(() => _currentIndex = index);
    setUrlHash(_tabNames[index]);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: _switchTab,
        type: BottomNavigationBarType.fixed,
        selectedItemColor: Theme.of(context).primaryColor,
        unselectedItemColor: Colors.grey,
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.home), label: 'Home'),
          BottomNavigationBarItem(icon: Icon(Icons.chat_bubble_outline), label: 'Assistant'),
          BottomNavigationBarItem(icon: Icon(Icons.qr_code_scanner), label: 'Scan'),
          BottomNavigationBarItem(icon: Icon(Icons.landscape), label: 'Farm'),
          BottomNavigationBarItem(icon: Icon(Icons.person), label: 'Profile'),
        ],
      ),
    );
  }
}
