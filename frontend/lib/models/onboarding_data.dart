class OnboardingData {
  static String? selectedLanguage;
  static String? farmName;
  static String? farmVillage;
  static String? farmDistrict;
  static String? farmState;
  static double? farmArea;
  static int? createdFarmId;

  static void reset() {
    selectedLanguage = null;
    farmName = null;
    farmVillage = null;
    farmDistrict = null;
    farmState = null;
    farmArea = null;
    createdFarmId = null;
  }
}
