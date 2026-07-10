import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/user.dart';

class AuthService extends ChangeNotifier {
  static const _tokenKey = 'access_token';
  static const _refreshKey = 'refresh_token';
  static const _userKey = 'user_data';

  String? _accessToken;
  String? _refreshToken;
  AppUser? _user;
  bool _initialized = false;

  String? get accessToken => _accessToken;
  String? get refreshToken => _refreshToken;
  AppUser? get user => _user;
  bool get isAuthenticated => _accessToken != null && _user != null;
  bool get isInitialized => _initialized;

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    _accessToken = prefs.getString(_tokenKey);
    _refreshToken = prefs.getString(_refreshKey);
    final userJson = prefs.getString(_userKey);
    if (userJson != null) {
      try {
        _user = AppUser.fromJson(json.decode(userJson));
      } catch (_) {
        _user = null;
      }
    }
    _initialized = true;
    notifyListeners();
  }

  Future<void> saveAuth({
    required String accessToken,
    required String refreshToken,
    required AppUser user,
  }) async {
    _accessToken = accessToken;
    _refreshToken = refreshToken;
    _user = user;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, accessToken);
    await prefs.setString(_refreshKey, refreshToken);
    await prefs.setString(_userKey, json.encode(user.toJson()));
    notifyListeners();
  }

  Future<void> updateUser(AppUser user) async {
    _user = user;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_userKey, json.encode(user.toJson()));
    notifyListeners();
  }

  Future<void> logout() async {
    _accessToken = null;
    _refreshToken = null;
    _user = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    await prefs.remove(_refreshKey);
    await prefs.remove(_userKey);
    notifyListeners();
  }

  Map<String, String> get authHeaders {
    if (_accessToken == null) return {};
    return {'Authorization': 'Bearer $_accessToken'};
  }
}
