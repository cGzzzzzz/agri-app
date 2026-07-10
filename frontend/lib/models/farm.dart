class AppFarm {
  final int id;
  final int userId;
  final String name;
  final String? village;
  final String? district;
  final String? state;
  final String country;
  final double? area;
  final String areaUnit;
  final double? latitude;
  final double? longitude;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  AppFarm({
    required this.id,
    required this.userId,
    required this.name,
    this.village,
    this.district,
    this.state,
    this.country = 'India',
    this.area,
    this.areaUnit = 'acre',
    this.latitude,
    this.longitude,
    this.createdAt,
    this.updatedAt,
  });

  factory AppFarm.fromJson(Map<String, dynamic> json) {
    return AppFarm(
      id: json['id'] as int,
      userId: json['user_id'] as int,
      name: json['name'] as String,
      village: json['village'] as String?,
      district: json['district'] as String?,
      state: json['state'] as String?,
      country: json['country'] as String? ?? 'India',
      area: (json['area'] as num?)?.toDouble(),
      areaUnit: json['area_unit'] as String? ?? 'acre',
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at']) : null,
      updatedAt: json['updated_at'] != null ? DateTime.tryParse(json['updated_at']) : null,
    );
  }

  Map<String, dynamic> toJson() => {
        'name': name,
        'village': village,
        'district': district,
        'state': state,
        'country': country,
        'area': area,
        'area_unit': areaUnit,
        'latitude': latitude,
        'longitude': longitude,
      };

  String get locationText {
    final parts = <String>[];
    if (village != null && village!.isNotEmpty) parts.add(village!);
    if (district != null && district!.isNotEmpty) parts.add(district!);
    if (state != null && state!.isNotEmpty) parts.add(state!);
    return parts.isEmpty ? country : parts.join(', ');
  }
}
