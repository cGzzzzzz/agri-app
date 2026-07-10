import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:image_picker/image_picker.dart';
import '../../services/api_service.dart';
import '../../services/auth_service.dart';

class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  bool _isAnalyzing = false;
  Map<String, dynamic>? _result;
  String? _imagePath;

  final ImagePicker _picker = ImagePicker();

  Future<void> _pickImage(ImageSource source) async {
    final XFile? picked = await _picker.pickImage(source: source, maxWidth: 1024, maxHeight: 1024, imageQuality: 85);
    if (picked == null) return;
    setState(() {
      _imagePath = picked.path;
      _isAnalyzing = true;
      _result = null;
    });
    await _analyze(picked.path);
  }

  Future<void> _analyze(String path) async {
    final auth = Provider.of<AuthService>(context, listen: false);
    final api = ApiService(auth);
    final result = await api.scanLeaf(path);
    if (mounted) {
      setState(() {
        _isAnalyzing = false;
        _result = result;
      });
    }
  }

  void _showImageSourceDialog() {
    showModalBottomSheet(
      context: context,
      builder: (ctx) => SafeArea(
        child: Wrap(
          children: [
            ListTile(
              leading: const Icon(Icons.camera_alt),
              title: const Text('Camera'),
              onTap: () { Navigator.pop(ctx); _pickImage(ImageSource.camera); },
            ),
            ListTile(
              leading: const Icon(Icons.photo_library),
              title: const Text('Gallery'),
              onTap: () { Navigator.pop(ctx); _pickImage(ImageSource.gallery); },
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final primaryColor = Theme.of(context).primaryColor;

    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(title: const Text('Vision Diagnosis')),
      body: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
        child: Center(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (!_isAnalyzing && _result == null) ...[
                Expanded(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      if (_imagePath != null)
                        ClipRRect(
                          borderRadius: BorderRadius.circular(12),
                          child: Image.file(File(_imagePath!), height: 160, fit: BoxFit.cover),
                        )
                      else ...[
                        Container(
                          width: 80, height: 80,
                          decoration: BoxDecoration(color: const Color(0xFFF1F3F5), borderRadius: BorderRadius.circular(40)),
                          child: const Icon(Icons.camera_alt_outlined, size: 36, color: Color(0xFF1C1E21)),
                        ),
                        const SizedBox(height: 24),
                      ],
                      Text(
                        'Vision Disease Analysis',
                        style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontSize: 22),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Capture or upload a leaf image for diagnostic analysis.',
                        style: Theme.of(context).textTheme.bodyMedium,
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                ),
                ElevatedButton(
                  onPressed: _showImageSourceDialog,
                  child: const Text('Select Image'),
                ),
              ],

              if (_isAnalyzing) ...[
                const Spacer(),
                if (_imagePath != null)
                  ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.file(File(_imagePath!), height: 120, fit: BoxFit.cover),
                  ),
                const SizedBox(height: 24),
                Center(
                  child: SizedBox(
                    width: 32, height: 32,
                    child: CircularProgressIndicator(strokeWidth: 3, valueColor: AlwaysStoppedAnimation<Color>(primaryColor)),
                  ),
                ),
                const SizedBox(height: 24),
                const Text('Vision Analysis in Progress', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold), textAlign: TextAlign.center),
                const SizedBox(height: 8),
                const Text('Segmenting leaf imagery and running classifier networks...', style: TextStyle(color: Colors.grey, fontSize: 13), textAlign: TextAlign.center),
                const Spacer(),
              ],

              if (_result != null) ...[
                Expanded(
                  child: SingleChildScrollView(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: 16),
                        if (_imagePath != null)
                          ClipRRect(
                            borderRadius: BorderRadius.circular(12),
                            child: Image.file(File(_imagePath!), height: 140, width: double.infinity, fit: BoxFit.cover),
                          ),
                        const SizedBox(height: 16),
                        Text('DIAGNOSIS REPORT', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Colors.grey.shade500, letterSpacing: 1.5)),
                        const SizedBox(height: 16),
                        _buildField('Disease', _extractDisease()),
                        _buildField('Confidence', _extractConfidence()),
                        _buildField('Severity', _extractSeverity()),
                        const SizedBox(height: 16),
                        Text('TREATMENT PROTOCOL', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Colors.grey.shade500, letterSpacing: 1.5)),
                        const SizedBox(height: 12),
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(color: Colors.grey.shade50, borderRadius: BorderRadius.circular(8), border: Border.all(color: Colors.grey.shade200)),
                          child: Text(_result!['response'] ?? _result!['recommendation'] ?? 'No recommendation provided.', style: const TextStyle(fontSize: 13, height: 1.5)),
                        ),
                      ],
                    ),
                  ),
                ),
                ElevatedButton(
                  onPressed: () => setState(() { _result = null; _imagePath = null; }),
                  child: const Text('New Analysis'),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  String _extractDisease() {
    final d = _result!;
    if (d['disease'] is Map) return d['disease']['label'] ?? 'Unknown';
    if (d['disease'] is String) return d['disease'];
    return 'Unknown';
  }

  String _extractConfidence() {
    final d = _result!;
    if (d['disease'] is Map) return '${((d['disease']['confidence'] ?? 0) * 100).toStringAsFixed(1)}%';
    if (d['confidence'] is String) return d['confidence'];
    return 'N/A';
  }

  String _extractSeverity() {
    final d = _result!;
    if (d['severity'] is Map) return '${d['severity']['label']} (${((d['severity']['score'] ?? 0) * 100).toStringAsFixed(0)}%)';
    if (d['severity'] is String) return d['severity'];
    return 'N/A';
  }

  Widget _buildField(String title, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title.toUpperCase(), style: TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: Colors.grey.shade400, letterSpacing: 1.0)),
          const SizedBox(height: 4),
          Text(value, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: Color(0xFF1C1E21))),
          const SizedBox(height: 12),
          const Divider(height: 1),
        ],
      ),
    );
  }
}
