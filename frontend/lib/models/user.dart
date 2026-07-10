class AppUser {
  final int id;
  final String email;
  final String? phone;
  final String name;
  final String language;
  final bool isActive;
  final DateTime? createdAt;

  AppUser({
    required this.id,
    required this.email,
    this.phone,
    required this.name,
    required this.language,
    required this.isActive,
    this.createdAt,
  });

  factory AppUser.fromJson(Map<String, dynamic> json) {
    return AppUser(
      id: json['id'] as int,
      email: json['email'] as String,
      phone: json['phone'] as String?,
      name: json['name'] as String,
      language: json['language'] as String? ?? 'en',
      isActive: json['is_active'] as bool? ?? true,
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at']) : null,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'email': email,
        'phone': phone,
        'name': name,
        'language': language,
        'is_active': isActive,
        'created_at': createdAt?.toIso8601String(),
      };

  String get initials {
    final parts = name.trim().split(RegExp(r'\s+'));
    if (parts.length >= 2) return '${parts[0][0]}${parts[1][0]}'.toUpperCase();
    if (parts.isNotEmpty && parts[0].isNotEmpty) return parts[0][0].toUpperCase();
    return '?';
  }
}
