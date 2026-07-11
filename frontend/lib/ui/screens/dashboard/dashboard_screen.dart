import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../models/crop.dart';
import '../../../services/api_service.dart';
import '../../../services/auth_service.dart';
import '../../../services/location_service.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  bool _isLoading = true;
  Map<String, dynamic> _weather = {};
  List<AppCrop> _crops = [];
  String _userName = 'Farmer';
  bool _gpsAvailable = false;
  String _gpsStatus = '';

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    try {
      final auth = Provider.of<AuthService>(context, listen: false);
      final api = ApiService(auth);

      final position = await LocationService.getCurrentLocation();
      if (mounted) {
        setState(() {
          _gpsAvailable = position != null;
          _gpsStatus = position != null ? '' : 'No GPS available';
        });
      }

      final results = await Future.wait([
        api.getWeather(lat: position?.latitude, lng: position?.longitude),
        api.listCrops(),
      ]);

      if (mounted) {
        setState(() {
          _weather = results[0] as Map<String, dynamic>;
          _crops = results[1] as List<AppCrop>;
          _userName = auth.user?.name ?? 'Farmer';
          _isLoading = false;
        });
      }
    } catch (e) {
      debugPrint('Dashboard load error: $e');
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final primaryColor = Theme.of(context).primaryColor;
    final borderLight = Colors.grey.shade200;

    if (_isLoading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final crop = _crops.isNotEmpty ? _crops.first : null;

    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text('AgriAI'),
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_outlined),
            onPressed: () {},
          ),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Welcome
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'FIELD PROFILE',
                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Colors.grey.shade500, letterSpacing: 1.5),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Hello, $_userName',
                    style: Theme.of(context).textTheme.displayLarge?.copyWith(fontSize: 28, fontWeight: FontWeight.w800),
                  ),
                ],
              ),
              const SizedBox(height: 24),

              // Weather
              if (!_gpsAvailable && _gpsStatus.isNotEmpty)
                Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: Colors.orange.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.orange.shade200),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.location_off_outlined, size: 16, color: Colors.orange.shade700),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(_gpsStatus, style: TextStyle(fontSize: 12, color: Colors.orange.shade700)),
                      ),
                    ],
                  ),
                ),
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Colors.grey.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: borderLight),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('WEATHER', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: Colors.grey.shade500, letterSpacing: 1.2)),
                          const SizedBox(height: 8),
                          Text(_weather['condition'] ?? 'Clear', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Colors.grey.shade800)),
                          const SizedBox(height: 4),
                          Text(_weather['advisory'] ?? _weather['description'] ?? '', style: TextStyle(fontSize: 12, color: Colors.grey.shade500), maxLines: 2, overflow: TextOverflow.ellipsis),
                        ],
                      ),
                    ),
                    const VerticalDivider(),
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16.0),
                      child: Column(
                        children: [
                          Text(
                            '${_weather['temperature_c'] ?? _weather['temperature'] ?? '--'}°',
                            style: TextStyle(fontSize: 28, fontWeight: FontWeight.w800, color: primaryColor),
                          ),
                          Text('TEMP', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: Colors.grey.shade500)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // Active crop
              Text('ACTIVE CULTIVATION', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Colors.grey.shade500, letterSpacing: 1.5)),
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(8), border: Border.all(color: borderLight)),
                child: crop != null
                    ? Column(
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                           _buildFieldMetric('Crop Type', crop.cropType),
                               _buildFieldMetric('Field Size', '${crop.fieldSize ?? '--'} Acres'),
                            ],
                          ),
                          const SizedBox(height: 16),
                          const Divider(),
                          const SizedBox(height: 16),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                               _buildFieldMetric('Variety', crop.cropVariety ?? 'Standard'),
                               _buildFieldMetric('Irrigation', crop.irrigationType ?? 'N/A'),
                            ],
                          ),
                        ],
                      )
                    : Center(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Text('No active crops. Register a crop from the Farm tab.', style: TextStyle(color: Colors.grey.shade500)),
                        ),
                      ),
              ),
              const SizedBox(height: 24),

              // Scan history
              Text('RECENT SCANS', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Colors.grey.shade500, letterSpacing: 1.5)),
              const SizedBox(height: 12),
              _RecentScansWidget(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFieldMetric(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label.toUpperCase(), style: TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: Colors.grey.shade400, letterSpacing: 1.0)),
        const SizedBox(height: 4),
        Text(value, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Color(0xFF1C1E21))),
      ],
    );
  }
}

class _RecentScansWidget extends StatefulWidget {
  @override
  State<_RecentScansWidget> createState() => _RecentScansWidgetState();
}

class _RecentScansWidgetState extends State<_RecentScansWidget> {
  List<Map<String, dynamic>> _scans = [];
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final auth = Provider.of<AuthService>(context, listen: false);
    final api = ApiService(auth);
    final scans = await api.getScanHistory();
    if (mounted) setState(() { _scans = scans; _loaded = true; });
  }

  @override
  Widget build(BuildContext context) {
    if (!_loaded) return const Center(child: Padding(padding: EdgeInsets.all(16), child: CircularProgressIndicator()));
    if (_scans.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(border: Border.all(color: Colors.grey.shade200), borderRadius: BorderRadius.circular(8)),
        child: Center(child: Text('No scans yet. Use the Scan tab to analyze a leaf.', style: TextStyle(color: Colors.grey.shade500))),
      );
    }
    return Column(
      children: _scans.take(3).map((scan) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(border: Border.all(color: Colors.grey.shade200), borderRadius: BorderRadius.circular(8)),
        child: Row(
          children: [
            Icon(Icons.bug_report_outlined, color: _severityColor(scan['severity']), size: 24),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(scan['disease'] ?? 'Unknown', style: const TextStyle(fontWeight: FontWeight.w600)),
                  Text('Confidence: ${(scan['confidence'] ?? 0).toStringAsFixed(0)}% · ${(scan['severity'] ?? 'N/A')}', style: TextStyle(fontSize: 12, color: Colors.grey.shade500)),
                ],
              ),
            ),
          ],
        ),
      )).toList(),
    );
  }

  Color _severityColor(dynamic severity) {
    final s = (severity ?? '').toString().toLowerCase();
    if (s.contains('high')) return const Color(0xFFD90429);
    if (s.contains('moderate')) return Colors.orange;
    return Colors.green;
  }
}
