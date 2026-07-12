import 'package:flutter/foundation.dart';

class OnboardingData extends ChangeNotifier {
  String? selectedLanguage;
  String? farmName;
  String? farmVillage;
  String? farmDistrict;
  String? farmState;
  double? farmArea;
  int? createdFarmId;

  void update({
    String? selectedLanguage,
    String? farmName,
    String? farmVillage,
    String? farmDistrict,
    String? farmState,
    double? farmArea,
    int? createdFarmId,
  }) {
    this.selectedLanguage = selectedLanguage ?? this.selectedLanguage;
    this.farmName = farmName ?? this.farmName;
    this.farmVillage = farmVillage ?? this.farmVillage;
    this.farmDistrict = farmDistrict ?? this.farmDistrict;
    this.farmState = farmState ?? this.farmState;
    this.farmArea = farmArea ?? this.farmArea;
    this.createdFarmId = createdFarmId ?? this.createdFarmId;
    notifyListeners();
  }

  void reset() {
    selectedLanguage = null;
    farmName = null;
    farmVillage = null;
    farmDistrict = null;
    farmState = null;
    farmArea = null;
    createdFarmId = null;
    notifyListeners();
  }
}
