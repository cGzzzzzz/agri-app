class AppCrop {
  final int id;
  final int farmId;
  final String cropType;
  final String? cropVariety;
  final String? sowingDate;
  final String? growthStage;
  final String? irrigationType;
  final String? fieldSize;
  final String? notes;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  AppCrop({
    required this.id,
    required this.farmId,
    required this.cropType,
    this.cropVariety,
    this.sowingDate,
    this.growthStage,
    this.irrigationType,
    this.fieldSize,
    this.notes,
    this.createdAt,
    this.updatedAt,
  });

  factory AppCrop.fromJson(Map<String, dynamic> json) {
    return AppCrop(
      id: json['id'] as int,
      farmId: json['farm_id'] as int,
      cropType: json['crop_type'] as String,
      cropVariety: json['crop_variety'] as String?,
      sowingDate: json['sowing_date'] as String?,
      growthStage: json['growth_stage'] as String?,
      irrigationType: json['irrigation_type'] as String?,
      fieldSize: json['field_size'] as String?,
      notes: json['notes'] as String?,
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at']) : null,
      updatedAt: json['updated_at'] != null ? DateTime.tryParse(json['updated_at']) : null,
    );
  }

  Map<String, dynamic> toJson() => {
        'farm_id': farmId,
        'crop_type': cropType,
        'crop_variety': cropVariety,
        'sowing_date': sowingDate,
        'growth_stage': growthStage,
        'irrigation_type': irrigationType,
        'field_size': fieldSize,
        'notes': notes,
      };
}
