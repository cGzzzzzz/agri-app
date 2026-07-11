const String apiPrefix = '/api/v1';

class ApiEndpoints {
  ApiEndpoints._();

  static const String register = '$apiPrefix/auth/register';
  static const String login = '$apiPrefix/auth/login';
  static const String refresh = '$apiPrefix/auth/refresh';
  static const String me = '$apiPrefix/auth/me';
  static const String updateProfile = '$apiPrefix/users/me';
  static const String changePassword = '$apiPrefix/auth/change-password';

  static const String farms = '$apiPrefix/farms';
  static String farmById(int id) => '$apiPrefix/farms/$id';

  static const String crops = '$apiPrefix/crops';
  static String cropById(int id) => '$apiPrefix/crops/$id';

  static const String chat = '$apiPrefix/chat';
  static const String chatHistory = '$apiPrefix/chat/history';

  static const String diseaseAnalyze = '$apiPrefix/disease/analyze';
  static const String diseaseHistory = '$apiPrefix/disease/history';

  static const String recommendations = '$apiPrefix/recommendations';
  static const String recommendationsHistory = '$apiPrefix/recommendations/history';

  static const String weatherCurrent = '$apiPrefix/weather/current';
  static String weatherForecast(int days) => '$apiPrefix/weather/forecast?days=$days';

  static const String sttTranscribe = '$apiPrefix/stt/transcribe';
}
