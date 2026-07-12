import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../models/user.dart';
import '../../services/api_service.dart';
import '../../services/auth_service.dart';
import 'auth/login_screen.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  AppUser? _user;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    final auth = Provider.of<AuthService>(context, listen: false);
    final api = ApiService(auth);
    final data = await api.getProfile();
    if (data != null && mounted) {
      setState(() => _user = AppUser.fromJson(data));
    }
  }

  void _showEditDialog() {
    final nameController = TextEditingController(text: _user?.name ?? '');
    final phoneController = TextEditingController(text: _user?.phone ?? '');
    String selectedLanguage = _user?.language ?? 'en';

    final languages = {
      'en': 'English',
      'ta': 'Tamil',
      'hi': 'Hindi',
      'te': 'Telugu',
      'kn': 'Kannada',
      'ml': 'Malayalam',
    };

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: const Text('Edit Profile'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: nameController,
                  decoration: const InputDecoration(labelText: 'Name'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: phoneController,
                  decoration: const InputDecoration(labelText: 'Phone'),
                  keyboardType: TextInputType.phone,
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: selectedLanguage,
                  decoration: const InputDecoration(labelText: 'Language'),
                  items: languages.entries
                      .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
                      .toList(),
                  onChanged: (v) {
                    if (v != null) setDialogState(() => selectedLanguage = v);
                  },
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
            ElevatedButton(
              onPressed: () async {
                final auth = Provider.of<AuthService>(context, listen: false);
                final api = ApiService(auth);
                final result = await api.updateProfile(
                  name: nameController.text.trim(),
                  phone: phoneController.text.trim(),
                  language: selectedLanguage,
                );
                if (result != null) {
                  final updated = AppUser.fromJson(result);
                  await auth.updateUser(updated);
                  if (mounted) setState(() => _user = updated);
                }
                if (ctx.mounted) Navigator.pop(ctx);
              },
              child: const Text('Save'),
            ),
          ],
        ),
      ),
    );
  }

  void _showChangePasswordDialog() {
    final currentController = TextEditingController();
    final newController = TextEditingController();
    final confirmController = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Change Password'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: currentController,
                decoration: const InputDecoration(labelText: 'Current Password'),
                obscureText: true,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: newController,
                decoration: const InputDecoration(labelText: 'New Password'),
                obscureText: true,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: confirmController,
                decoration: const InputDecoration(labelText: 'Confirm Password'),
                obscureText: true,
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () async {
              if (newController.text != confirmController.text) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Passwords do not match')),
                );
                return;
              }
              final auth = Provider.of<AuthService>(context, listen: false);
              final api = ApiService(auth);
              final success = await api.changePassword(
                currentPassword: currentController.text,
                newPassword: newController.text,
              );
              if (ctx.mounted) Navigator.pop(ctx);
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text(success ? 'Password changed' : 'Failed to change password')),
                );
              }
            },
            child: const Text('Change'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthService>(context);
    final user = _user ?? auth.user;
    final borderLight = Colors.grey.shade200;

    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(title: const Text('My Profile')),
      body: user == null
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Avatar + name
                  Center(
                    child: Column(
                      children: [
                        CircleAvatar(
                          radius: 40,
                          backgroundColor: Theme.of(context).primaryColor.withValues(alpha: 0.1),
                          child: Text(
                            user.initials,
                            style: TextStyle(
                              fontSize: 28,
                              fontWeight: FontWeight.bold,
                              color: Theme.of(context).primaryColor,
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          user.name,
                          style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                        ),
                        Text(
                          user.email,
                          style: TextStyle(fontSize: 14, color: Colors.grey.shade500),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 32),

                  // Info cards
                  Text(
                    'ACCOUNT DETAILS',
                    style: TextStyle(
                      fontSize: 11, fontWeight: FontWeight.w700,
                      color: Colors.grey.shade500, letterSpacing: 1.5,
                    ),
                  ),
                  const SizedBox(height: 12),
                  _buildInfoTile(Icons.person_outlined, 'Name', user.name, borderLight),
                  _buildInfoTile(Icons.email_outlined, 'Email', user.email, borderLight),
                  _buildInfoTile(Icons.phone_outlined, 'Phone', user.phone ?? 'Not set', borderLight),
                  _buildInfoTile(
                    Icons.language,
                    'Language',
                    {'en': 'English', 'ta': 'Tamil', 'hi': 'Hindi', 'te': 'Telugu', 'kn': 'Kannada', 'ml': 'Malayalam'}[user.language] ?? user.language,
                    borderLight,
                  ),
                  _buildInfoTile(Icons.calendar_today, 'Member since',
                      user.createdAt != null ? '${user.createdAt!.day}/${user.createdAt!.month}/${user.createdAt!.year}' : 'N/A',
                      borderLight),
                  const SizedBox(height: 24),

                  // Actions
                  Text(
                    'SETTINGS',
                    style: TextStyle(
                      fontSize: 11, fontWeight: FontWeight.w700,
                      color: Colors.grey.shade500, letterSpacing: 1.5,
                    ),
                  ),
                  const SizedBox(height: 12),
                  _buildActionTile(Icons.edit_outlined, 'Edit Profile', _showEditDialog, borderLight),
                  _buildActionTile(Icons.lock_outlined, 'Change Password', _showChangePasswordDialog, borderLight),
                  const SizedBox(height: 24),

                  // Logout
                  SizedBox(
                    width: double.infinity,
                    child: Builder(
                      builder: (context) {
                        final auth = Provider.of<AuthService>(context, listen: false);
                        return OutlinedButton.icon(
                          onPressed: () async {
                            await auth.logout();
                            if (!context.mounted) return;
                            Navigator.of(context).pushAndRemoveUntil(
                              MaterialPageRoute(builder: (_) => const LoginScreen()),
                              (route) => false,
                            );
                          },
                          icon: const Icon(Icons.logout, color: Color(0xFFD90429)),
                          label: const Text('Sign Out', style: TextStyle(color: Color(0xFFD90429))),
                          style: OutlinedButton.styleFrom(
                            side: const BorderSide(color: Color(0xFFD90429)),
                            padding: const EdgeInsets.symmetric(vertical: 14),
                          ),
                        );
                      },
                    ),
                  ),
                  const SizedBox(height: 24),
                ],
              ),
            ),
    );
  }

  Widget _buildInfoTile(IconData icon, String label, String value, Color borderLight) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        border: Border.all(color: borderLight),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(icon, size: 20, color: Colors.grey.shade500),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label.toUpperCase(), style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: Colors.grey.shade400, letterSpacing: 1)),
                const SizedBox(height: 2),
                Text(value, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionTile(IconData icon, String label, VoidCallback onTap, Color borderLight) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          border: Border.all(color: borderLight),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            Icon(icon, size: 20, color: Theme.of(context).primaryColor),
            const SizedBox(width: 16),
            Expanded(child: Text(label, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600))),
            Icon(Icons.chevron_right, color: Colors.grey.shade400),
          ],
        ),
      ),
    );
  }
}
