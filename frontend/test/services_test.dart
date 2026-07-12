import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/models/onboarding_data.dart';
import 'package:frontend/models/user.dart';
import 'package:frontend/services/auth_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('AuthService', () {
    late AuthService auth;

    setUp(() {
      auth = AuthService();
    });

    test('starts unauthenticated', () {
      expect(auth.isAuthenticated, isFalse);
      expect(auth.accessToken, isNull);
      expect(auth.user, isNull);
    });

    test('isInitialized defaults to false', () {
      expect(auth.isInitialized, isFalse);
    });

    test('authHeaders returns empty when no token', () {
      expect(auth.authHeaders, isEmpty);
    });

    test('authHeaders returns Bearer token when set', () async {
      await auth.saveAuth(
        accessToken: 'test-token',
        refreshToken: 'refresh-token',
        user: AppUser(id: 1, name: 'Test', email: 'test@test.com', phone: '123', language: 'en', isActive: true),
      );
      expect(auth.authHeaders, {'Authorization': 'Bearer test-token'});
    });

    test('logout clears all state', () async {
      await auth.saveAuth(
        accessToken: 'test-token',
        refreshToken: 'refresh-token',
        user: AppUser(id: 1, name: 'Test', email: 'test@test.com', phone: '123', language: 'en', isActive: true),
      );
      expect(auth.isAuthenticated, isTrue);

      await auth.logout();
      expect(auth.isAuthenticated, isFalse);
      expect(auth.accessToken, isNull);
      expect(auth.refreshToken, isNull);
      expect(auth.user, isNull);
    });

    test('notifyListeners is called on state changes', () async {
      var notified = false;
      auth.addListener(() => notified = true);

      await auth.logout();
      expect(notified, isTrue);
    });
  });

  group('OnboardingData', () {
    late OnboardingData data;

    setUp(() {
      data = OnboardingData();
    });

    test('starts with all null fields', () {
      expect(data.selectedLanguage, isNull);
      expect(data.farmName, isNull);
      expect(data.farmVillage, isNull);
      expect(data.farmDistrict, isNull);
      expect(data.farmState, isNull);
      expect(data.farmArea, isNull);
      expect(data.createdFarmId, isNull);
    });

    test('update sets fields and notifies', () {
      var notified = false;
      data.addListener(() => notified = true);

      data.update(farmName: 'Test Farm', farmArea: 10.5);
      expect(data.farmName, 'Test Farm');
      expect(data.farmArea, 10.5);
      expect(notified, isTrue);
    });

    test('update preserves existing fields', () {
      data.update(farmName: 'Farm A', farmArea: 5.0);
      data.update(farmVillage: 'Village B');

      expect(data.farmName, 'Farm A');
      expect(data.farmArea, 5.0);
      expect(data.farmVillage, 'Village B');
    });

    test('reset clears all fields and notifies', () {
      data.update(farmName: 'Farm', selectedLanguage: 'en', createdFarmId: 42);
      data.reset();

      expect(data.farmName, isNull);
      expect(data.selectedLanguage, isNull);
      expect(data.createdFarmId, isNull);
    });
  });
}
