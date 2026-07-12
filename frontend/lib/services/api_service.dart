import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../core/constants/api_constants.dart';
import '../models/crop.dart';
import '../models/farm.dart';
import '../services/auth_service.dart';
import '../main.dart' show navigatorKey;

class ApiService {
  final AuthService _auth;
  ApiService(this._auth);

  // The NIM container may need time to accept work during GPU load spikes.
  static const _timeout = Duration(seconds: 60);

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        ..._auth.authHeaders,
      };

  Future<Map<String, dynamic>?> _get(String url) async {
    try {
      final response = await http.get(Uri.parse('${Api.baseUrl}$url'), headers: _headers).timeout(_timeout);
      if (response.statusCode == 200) {
        final body = json.decode(response.body);
        return body is Map<String, dynamic> ? body : null;
      }
      if (response.statusCode == 401) {
        await _handleUnauthorized();
      }
    } catch (e) {
      debugPrint('GET $url error: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>?> _post(String url, Map<String, dynamic> data, {Duration? timeout}) async {
    try {
      final response = await http.post(
        Uri.parse('${Api.baseUrl}$url'),
        headers: _headers,
        body: json.encode(data),
      ).timeout(timeout ?? _timeout);
      if (response.statusCode == 200 || response.statusCode == 201 || response.statusCode == 202) {
        return json.decode(response.body) as Map<String, dynamic>;
      }
      if (response.statusCode == 401) {
        await _handleUnauthorized();
      }
    } catch (e) {
      debugPrint('POST $url error: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>?> _patch(String url, Map<String, dynamic> data) async {
    try {
      final response = await http.patch(
        Uri.parse('${Api.baseUrl}$url'),
        headers: _headers,
        body: json.encode(data),
      ).timeout(_timeout);
      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      }
      if (response.statusCode == 401) {
        await _handleUnauthorized();
      }
    } catch (e) {
      debugPrint('PATCH $url error: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>?> _delete(String url) async {
    try {
      final response = await http.delete(Uri.parse('${Api.baseUrl}$url'), headers: _headers).timeout(_timeout);
      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      }
      if (response.statusCode == 401) {
        await _handleUnauthorized();
      }
    } catch (e) {
      debugPrint('DELETE $url error: $e');
    }
    return null;
  }

  Future<void> _handleUnauthorized() async {
    debugPrint('401 Unauthorized - attempting token refresh');
    final refreshed = await _tryRefreshToken();
    if (!refreshed) {
      debugPrint('Token refresh failed - logging out');
      _auth.logout();
      navigatorKey.currentState?.pushNamedAndRemoveUntil('/', (route) => false);
    }
  }

  Future<bool> _tryRefreshToken() async {
    final refreshToken = _auth.refreshToken;
    if (refreshToken == null) return false;

    try {
      final response = await http.post(
        Uri.parse('${Api.baseUrl}${ApiEndpoints.refresh}'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'refresh_token': refreshToken}),
      ).timeout(_timeout);

      if (response.statusCode == 200) {
        final body = json.decode(response.body);
        final data = body['data'];
        if (data != null && data['tokens'] != null) {
          final tokens = data['tokens'] as Map<String, dynamic>;
          await _auth.saveAuth(
            accessToken: tokens['access_token'],
            refreshToken: tokens['refresh_token'],
            user: _auth.user!,
          );
          debugPrint('Token refreshed successfully');
          return true;
        }
      }
    } catch (e) {
      debugPrint('Token refresh error: $e');
    }
    return false;
  }

  Map<String, dynamic>? _extractData(Map<String, dynamic>? response) {
    if (response == null) return null;
    if (response['data'] is Map) return response['data'] as Map<String, dynamic>;
    return response;
  }

  List<dynamic>? _extractList(Map<String, dynamic>? response) {
    if (response == null) return null;
    if (response['data'] is List) return response['data'] as List<dynamic>;
    return null;
  }

  // ─── Auth ───

  Future<Map<String, dynamic>?> register({
    required String email,
    required String password,
    required String name,
    String? phone,
    String language = 'en',
  }) async {
    final result = await _post(ApiEndpoints.register, {
      'email': email,
      'password': password,
      'name': name,
      'phone': phone,
      'language': language,
    });
    return _extractData(result);
  }

  Future<Map<String, dynamic>?> login({
    required String email,
    required String password,
  }) async {
    final result = await _post(ApiEndpoints.login, {
      'email': email,
      'password': password,
    });
    return _extractData(result);
  }

  Future<Map<String, dynamic>?> getProfile() async {
    final result = await _get(ApiEndpoints.me);
    return _extractData(result);
  }

  Future<Map<String, dynamic>?> updateProfile({
    String? name,
    String? phone,
    String? language,
  }) async {
    final data = <String, dynamic>{};
    if (name != null) data['name'] = name;
    if (phone != null) data['phone'] = phone;
    if (language != null) data['language'] = language;
    if (data.isEmpty) return null;
    final result = await _patch(ApiEndpoints.updateProfile, data);
    return _extractData(result);
  }

  Future<bool> changePassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    final result = await _post(ApiEndpoints.changePassword, {
      'current_password': currentPassword,
      'new_password': newPassword,
    });
    return result != null && result['success'] == true;
  }

  // ─── Farms ───

  Future<List<AppFarm>> listFarms() async {
    final result = await _get(ApiEndpoints.farms);
    final list = _extractList(result);
    if (list == null) return [];
    return list.map((e) => AppFarm.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<AppFarm?> createFarm({
    required String name,
    String? village,
    String? district,
    String? state,
    double? area,
  }) async {
    final result = await _post(ApiEndpoints.farms, {
      'name': name,
      'village': village,
      'district': district,
      'state': state,
      'area': area,
    });
    final data = _extractData(result);
    if (data != null) return AppFarm.fromJson(data);
    return null;
  }

  Future<AppFarm?> updateFarm(int farmId, Map<String, dynamic> fields) async {
    final result = await _patch(ApiEndpoints.farmById(farmId), fields);
    final data = _extractData(result);
    if (data != null) return AppFarm.fromJson(data);
    return null;
  }

  Future<bool> deleteFarm(int farmId) async {
    final result = await _delete(ApiEndpoints.farmById(farmId));
    return result != null;
  }

  // ─── Crops ───

  Future<List<AppCrop>> listCrops() async {
    final result = await _get(ApiEndpoints.crops);
    final list = _extractList(result);
    if (list == null) return [];
    return list.map((e) => AppCrop.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<AppCrop?> createCrop({
    required int farmId,
    required String cropType,
    String? cropVariety,
    String? sowingDate,
    String? fieldSize,
  }) async {
    final result = await _post(ApiEndpoints.crops, {
      'farm_id': farmId,
      'crop_type': cropType,
      'crop_variety': cropVariety,
      'sowing_date': sowingDate,
      'field_size': fieldSize,
    });
    final data = _extractData(result);
    if (data != null) return AppCrop.fromJson(data);
    return null;
  }

  Future<AppCrop?> updateCrop(int cropId, Map<String, dynamic> fields) async {
    final result = await _patch(ApiEndpoints.cropById(cropId), fields);
    final data = _extractData(result);
    if (data != null) return AppCrop.fromJson(data);
    return null;
  }

  Future<bool> deleteCrop(int cropId) async {
    final result = await _delete(ApiEndpoints.cropById(cropId));
    return result != null;
  }

  // ─── Weather ───

  Future<Map<String, dynamic>> getWeather({String? location, double? lat, double? lng}) async {
    String url;
    if (lat != null && lng != null) {
      url = '${ApiEndpoints.weatherCurrent}?lat=$lat&lng=$lng';
    } else if (location != null) {
      url = '${ApiEndpoints.weatherCurrent}?location=$location';
    } else {
      url = ApiEndpoints.weatherCurrent;
    }
    final result = await _get(url);
    final data = _extractData(result);
    if (data != null) return data;
    return {
      'temperature_c': 31.0,
      'condition': 'Sunny with Rain expected',
      'advisory': 'Rain expected in 5 hours (Offline Mode)',
      'humidity_percent': 90,
      'precipitation_probability_percent': 84,
    };
  }

  Future<List<Map<String, dynamic>>> getWeatherForecast({int days = 5}) async {
    final result = await _get(ApiEndpoints.weatherForecast(days));
    final data = _extractData(result);
    if (data != null && data['days'] is List) {
      return (data['days'] as List).cast<Map<String, dynamic>>();
    }
    return [];
  }

  // ─── Disease / Scan ───

  Future<Map<String, dynamic>?> scanLeaf(String filePath, {int? farmId, int? cropId}) async {
    try {
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('${Api.baseUrl}${ApiEndpoints.diseaseAnalyze}'),
      );
      request.files.add(await http.MultipartFile.fromPath('file', filePath));
      if (farmId != null) request.fields['farm_id'] = farmId.toString();
      if (cropId != null) request.fields['crop_id'] = cropId.toString();

      final headers = _auth.authHeaders;
      headers.forEach((k, v) => request.headers[k] = v);

      final streamedResponse = await request.send().timeout(_timeout);
      final response = await http.Response.fromStream(streamedResponse);
      if (response.statusCode == 200) {
        final body = json.decode(response.body) as Map<String, dynamic>;
        return _extractData(body);
      }
    } catch (e) {
      debugPrint('Scan API error: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>?> scanLeafBytes(Uint8List bytes, {String fileName = 'leaf.jpg', int? farmId, int? cropId, String? cropType}) async {
    try {
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('${Api.baseUrl}${ApiEndpoints.diseaseAnalyze}'),
      );
      request.files.add(http.MultipartFile.fromBytes('file', bytes, filename: fileName));
      if (farmId != null) request.fields['farm_id'] = farmId.toString();
      if (cropId != null) request.fields['crop_id'] = cropId.toString();
      if (cropType != null && cropType.isNotEmpty) request.fields['crop'] = cropType;

      final headers = _auth.authHeaders;
      headers.forEach((k, v) => request.headers[k] = v);

      final streamedResponse = await request.send().timeout(_timeout);
      final response = await http.Response.fromStream(streamedResponse);
      if (response.statusCode == 200) {
        final body = json.decode(response.body) as Map<String, dynamic>;
        return _extractData(body);
      }
    } catch (e) {
      debugPrint('Scan bytes API error: $e');
    }
    return null;
  }

  Future<List<Map<String, dynamic>>> getScanHistory() async {
    final result = await _get(ApiEndpoints.diseaseHistory);
    final list = _extractList(result);
    if (list == null) return [];
    return list.cast<Map<String, dynamic>>();
  }

  // ─── Chat ───

  Future<Map<String, dynamic>?> sendMessage(
    String message, {
    int? farmId,
    int? cropId,
    String responseLanguage = 'en',
  }) async {
    final result = await _post(ApiEndpoints.chat, {
      'message': message,
      'farm_id': farmId,
      'crop_id': cropId,
      'response_language': responseLanguage,
    });
    return _extractData(result);
  }

  Future<Map<String, dynamic>?> getChatStatus(int messageId) async {
    final result = await _get(ApiEndpoints.chatStatus(messageId));
    return _extractData(result);
  }

  Future<List<Map<String, dynamic>>> getChatHistory() async {
    final result = await _get(ApiEndpoints.chatHistory);
    final list = _extractList(result);
    if (list == null) return [];
    return list.cast<Map<String, dynamic>>();
  }

  // ─── Recommendations ───

  Future<Map<String, dynamic>?> getRecommendation({
    required String crop,
    String? disease,
    String? severity,
    int? farmId,
    int? cropId,
  }) async {
    final result = await _post(ApiEndpoints.recommendations, {
      'crop': crop,
      'disease': disease,
      'severity': severity,
      'farm_id': farmId,
      'crop_id': cropId,
    });
    return _extractData(result);
  }

  Future<List<Map<String, dynamic>>> getRecommendationHistory() async {
    final result = await _get(ApiEndpoints.recommendationsHistory);
    final list = _extractList(result);
    if (list == null) return [];
    return list.cast<Map<String, dynamic>>();
  }

  Future<Map<String, String?>> transcribeAudio(Uint8List audioBytes, String filename, {String language = 'en', int sampleRate = 48000, int channels = 1}) async {
    try {
      final uri = Uri.parse('${Api.baseUrl}/api/v1/stt/transcribe');
      final request = http.MultipartRequest('POST', uri)
        ..headers.addAll(_auth.authHeaders)
        ..fields['language'] = language
        ..fields['sample_rate'] = sampleRate.toString()
        ..fields['channels'] = channels.toString()
        ..files.add(http.MultipartFile.fromBytes('file', audioBytes, filename: filename));
      final streamed = await request.send().timeout(_timeout);
      final response = await http.Response.fromStream(streamed);
      final body = json.decode(response.body);
      if (response.statusCode == 200 && body['success'] == true) {
        final data = body['data'];
        if (data is Map<String, dynamic>) return {'text': data['text'] as String?};
      }
      return {'error': body['message'] as String? ?? 'Transcription failed'};
    } catch (e) {
      debugPrint('transcribeAudio error: $e');
      return {'error': 'Network error — is the backend running?'};
    }
  }
}

class Api {
  static String get baseUrl {
    if (kIsWeb) return '';
    return 'http://192.168.0.199:8000';
  }
}
