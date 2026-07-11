import 'dart:async';
import 'dart:math';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:record/record.dart';
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:speech_to_text/speech_to_text.dart';

import '../../../core/theme/app_theme.dart';
import '../../../services/api_service.dart';
import '../../../services/auth_service.dart';

class AssistantScreen extends StatefulWidget {
  const AssistantScreen({super.key});

  @override
  State<AssistantScreen> createState() => _AssistantScreenState();
}

class _AssistantScreenState extends State<AssistantScreen>
    with SingleTickerProviderStateMixin {
  final List<Map<String, dynamic>> messages = [];
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  bool _isResponding = false;
  bool _historyLoaded = false;
  Timer? _chatPollTimer;
  int? _pendingMessageId;

  final SpeechToText _speech = SpeechToText();
  bool _speechAvailable = false;
  bool _isListening = false;
  String _lastWords = '';

  final AudioRecorder _recorder = AudioRecorder();
  bool _isRecording = false;
  bool _isTranscribing = false;
  final List<Uint8List> _audioChunks = [];
  StreamSubscription<Uint8List>? _audioSub;

  // VAD state
  double _noiseFloor = -60.0;
  double _speechPeak = -30.0;
  bool _hasSeenSpeech = false;
  DateTime? _silenceStart;

  static const double _silenceThresholdDb = -40.0;
  static const double _noiseAlpha = 0.05;
  static const double _speechAlpha = 0.1;
  static const double _thresholdPosition = 0.35;
  static const double _minSnrdB = 6.0;
  static const int _silenceTimeoutSeconds = 2;

  String _selectedLocale = 'en_US';

  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  static const _locales = <String, String>{
    'English': 'en_US',
    'Hindi': 'hi_IN',
    'Tamil': 'ta_IN',
    'Telugu': 'te_IN',
    'Kannada': 'kn_IN',
    'Bengali': 'bn_IN',
    'Marathi': 'mr_IN',
    'Gujarati': 'gu_IN',
    'Punjabi': 'pa_IN',
    'Malayalam': 'ml_IN',
    'Urdu': 'ur_IN',
    'Thai': 'th_TH',
    'Vietnamese': 'vi_VN',
    'Indonesian': 'id_ID',
  };

  String get _whisperLanguage => _selectedLocale.split('_').first;
  String get _selectedResponseLanguage => _selectedLocale.split('_').first.toLowerCase();

  String? _normalizedText(dynamic value) {
    if (value is! String) return null;
    final text = value.trim();
    return text.isEmpty ? null : text;
  }

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    )..repeat(reverse: true);
    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.3).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadHistory();
    });
    if (!kIsWeb) _initSpeech();
  }

  @override
  void dispose() {
    _chatPollTimer?.cancel();
    _speech.cancel();
    _recorder.dispose();
    _pulseController.dispose();
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(0,
            duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
      }
    });
  }

  // ─── VAD: Energy-based silence detection ─────────────────────────────────

  double _computeRmsDb(Uint8List pcm16Bytes) {
    final samples = pcm16Bytes.buffer.asInt16List();
    if (samples.isEmpty) return -96.0;
    double sumOfSquares = 0.0;
    for (int i = 0; i < samples.length; i++) {
      final normalized = samples[i] / 32768.0;
      sumOfSquares += normalized * normalized;
    }
    final rms = sqrt(sumOfSquares / samples.length);
    if (rms <= 0.0) return -96.0;
    return 20.0 * (log(rms) / ln10);
  }

  void _processVadChunk(Uint8List chunk) {
    final dbfs = _computeRmsDb(chunk);

    final currentThreshold =
        _noiseFloor + (_speechPeak - _noiseFloor) * _thresholdPosition;
    final bool isSilent =
        dbfs < currentThreshold || dbfs < _silenceThresholdDb;
    final bool isSpeech = (dbfs - _noiseFloor) > _minSnrdB;

    if (isSpeech) {
      _speechPeak += _speechAlpha * (dbfs - _speechPeak);
      _hasSeenSpeech = true;
      _silenceStart = null;
    } else {
      _noiseFloor += _noiseAlpha * (dbfs - _noiseFloor);
    }

    if (isSilent && _hasSeenSpeech && (_speechPeak - _noiseFloor) >= _minSnrdB) {
      if (_silenceStart == null) {
        _silenceStart = DateTime.now();
      } else if (DateTime.now().difference(_silenceStart!).inSeconds >= _silenceTimeoutSeconds) {
        _stopRecordingAndTranscribe();
      }
    }
  }

  void _resetVad() {
    _noiseFloor = -60.0;
    _speechPeak = -30.0;
    _hasSeenSpeech = false;
    _silenceStart = null;
  }

  // ─── Mobile: speech_to_text ────────────────────────────────────────────────

  Future<void> _initSpeech() async {
    try {
      _speechAvailable = await _speech.initialize(
        onError: (error) {
          debugPrint('Speech error: ${error.errorMsg}');
          if (mounted) setState(() => _isListening = false);
        },
        onStatus: (status) {
          debugPrint('Speech status: $status');
          if (status == 'notListening' || status == 'done') {
            if (mounted) setState(() => _isListening = false);
          }
        },
      );
    } catch (e) {
      debugPrint('Speech init failed: $e');
      _speechAvailable = false;
    }
    if (mounted) setState(() {});
  }

  Future<void> _startMobileListening() async {
    if (!_speechAvailable) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content:
                  Text('Speech recognition not available. Use Chrome or Edge.')),
        );
      }
      return;
    }
    _lastWords = '';
    await _speech.listen(
      onResult: _onSpeechResult,
      listenOptions: SpeechListenOptions(
        localeId: _selectedLocale,
        listenMode: ListenMode.dictation,
        cancelOnError: false,
        partialResults: true,
      ),
    );
    if (mounted) setState(() => _isListening = true);
  }

  Future<void> _stopMobileListening() async {
    await _speech.stop();
    if (mounted) setState(() => _isListening = false);
    if (_lastWords.trim().isNotEmpty) {
      _controller.text = _lastWords.trim();
      _sendMessage();
    }
  }

  void _onSpeechResult(SpeechRecognitionResult result) {
    if (mounted) {
      setState(() {
        _lastWords = result.recognizedWords;
        _controller.text = _lastWords;
        _controller.selection = TextSelection.fromPosition(
            TextPosition(offset: _controller.text.length));
      });
    }
  }

  // ─── Web: record + VAD + backend STT ──────────────────────────────────────

  Future<void> _startRecording() async {
    if (!await _recorder.hasPermission()) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Microphone permission denied.')),
        );
      }
      return;
    }
    _audioChunks.clear();
    _resetVad();
    final stream = await _recorder.startStream(
      const RecordConfig(encoder: AudioEncoder.pcm16bits, sampleRate: 48000, numChannels: 1),
    );
    _audioSub = stream.listen((data) {
      _audioChunks.add(Uint8List.fromList(data));
      _processVadChunk(data);
    });
    if (mounted) setState(() => _isRecording = true);
  }

  Future<void> _stopRecordingAndTranscribe() async {
    if (!_isRecording) return;
    await _audioSub?.cancel();
    _audioSub = null;
    await _recorder.stop();
    if (mounted) setState(() => _isRecording = false);

    int totalLength = 0;
    for (final chunk in _audioChunks) {
      totalLength += chunk.length;
    }

    Uint8List? audioBytes;
    if (_audioChunks.isNotEmpty && totalLength > 0) {
      audioBytes = Uint8List(totalLength);
      int offset = 0;
      for (final chunk in _audioChunks) {
        audioBytes.setRange(offset, offset + chunk.length, chunk);
        offset += chunk.length;
      }
    }
    _audioChunks.clear();

    if (audioBytes == null || audioBytes.isEmpty) {
      if (mounted) {
        setState(() => _isTranscribing = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No audio captured. Try again.')),
        );
      }
      return;
    }

    if (mounted) setState(() => _isTranscribing = true);

    final auth = Provider.of<AuthService>(context, listen: false);
    final api = ApiService(auth);
    final result = await api.transcribeAudio(
      audioBytes,
      'voice_${DateTime.now().millisecondsSinceEpoch}.pcm',
      language: _whisperLanguage,
      sampleRate: 48000,
      channels: 1,
    );

    if (mounted) {
      setState(() => _isTranscribing = false);
      final text = result['text'];
      final error = result['error'];
      if (text != null && text.trim().isNotEmpty) {
        _controller.text = text.trim();
        _sendMessage();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(error ?? 'Could not understand. Please try speaking again.')),
        );
      }
    }
  }

  // ─── Shared ────────────────────────────────────────────────────────────────

  void _toggleVoice() {
    if (kIsWeb) {
      _isRecording ? _stopRecordingAndTranscribe() : _startRecording();
    } else {
      _isListening ? _stopMobileListening() : _startMobileListening();
    }
  }

  bool get _isAnyVoiceActive => kIsWeb ? _isRecording : _isListening;

  Future<void> _loadHistory() async {
    final auth = Provider.of<AuthService>(context, listen: false);
    final api = ApiService(auth);
    final history = await api.getChatHistory();
    if (mounted && history.isNotEmpty) {
      setState(() {
        for (final h in history.reversed) {
          final question = _normalizedText(h['question'] ?? h['message']);
          final response = _normalizedText(h['response']);
          final errorMessage = _normalizedText(h['error_message']);

          if (question != null) {
            messages.add({'text': question, 'isUser': true});
          }

          if (h['status'] == 'completed') {
            if (response != null) {
              messages.add({'text': response, 'isUser': false});
            } else {
              messages.add({
                'text': 'A previous assistant reply was empty.',
                'isUser': false,
                'isError': true,
              });
            }
          } else if (h['status'] == 'pending' || h['status'] == 'processing') {
            _pendingMessageId = h['id'] as int?;
            _isResponding = _pendingMessageId != null;
          } else if (h['status'] == 'failed') {
            messages.add({
              'text': errorMessage ?? 'A previous assistant reply failed to generate.',
              'isUser': false,
              'isError': true,
            });
          }
        }
        _historyLoaded = true;
      });
    }
    if (!_historyLoaded && mounted) {
      final userName = auth.user?.name ?? 'Farmer';
      setState(() {
        messages.add({
          'text':
              'Hello $userName! I can help with crop diseases, weather, and farm management. How can I assist you today?',
          'isUser': false,
        });
        _historyLoaded = true;
      });
    }
    _scrollToBottom();
    if (_pendingMessageId != null) _startChatPolling(_pendingMessageId!);
  }

  Future<void> _sendMessage() async {
    final query = _controller.text.trim();
    if (query.isEmpty) return;

    setState(() {
      messages.add({'text': query, 'isUser': true});
      _isResponding = true;
      _controller.clear();
    });
    _scrollToBottom();

    final auth = Provider.of<AuthService>(context, listen: false);
    final api = ApiService(auth);
    final accepted = await api.sendMessage(
      query,
      responseLanguage: _selectedResponseLanguage,
    );
    final messageId = accepted?['message_id'];
    if (messageId is int) {
      _startChatPolling(messageId);
      return;
    }

    if (mounted) {
      setState(() {
        messages.add({'text': 'Your message could not be submitted. Please check the connection and try again.', 'isUser': false, 'isError': true});
        _isResponding = false;
      });
      _scrollToBottom();
    }
  }

  void _startChatPolling(int messageId) {
    _chatPollTimer?.cancel();
    _pendingMessageId = messageId;
    _chatPollTimer = Timer.periodic(const Duration(seconds: 2), (timer) async {
      final auth = Provider.of<AuthService>(context, listen: false);
      final status = await ApiService(auth).getChatStatus(messageId);
      if (!mounted || status == null) return;

      final state = status['status'];
      if (state == 'completed') {
        timer.cancel();
        final response = status['response'] as String?;
        setState(() {
          if (response != null && response.isNotEmpty) {
            messages.add({'text': response, 'isUser': false});
          }
          _pendingMessageId = null;
          _isResponding = false;
        });
        _scrollToBottom();
      } else if (state == 'failed') {
        timer.cancel();
        setState(() {
          messages.add({'text': 'The AI response could not be generated. Please try again.', 'isUser': false, 'isError': true});
          _pendingMessageId = null;
          _isResponding = false;
        });
        _scrollToBottom();
      }
    });
  }

  void _showLocalePicker() {
    showModalBottomSheet(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: Text('Assistant Language',
                  style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: Colors.grey.shade800)),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text(
                'Assistant replies follow this selection. Default is English.',
                style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
              ),
            ),
            const SizedBox(height: 8),
            Flexible(
              child: ListView(
                shrinkWrap: true,
                children: _locales.entries.map((entry) {
                  final selected = entry.value == _selectedLocale;
                  return ListTile(
                    leading: selected
                        ? Icon(Icons.check,
                            color: Theme.of(context).primaryColor)
                        : const SizedBox(width: 24),
                    title: Text(entry.key),
                    subtitle: Text(entry.value,
                        style: TextStyle(
                            fontSize: 12, color: Colors.grey.shade500)),
                    selected: selected,
                    onTap: () {
                      setState(() => _selectedLocale = entry.value);
                      Navigator.pop(ctx);
                    },
                  );
                }).toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String get _currentLanguageLabel {
    return _locales.entries
        .firstWhere((e) => e.value == _selectedLocale,
            orElse: () => const MapEntry('English', 'en_US'))
        .key;
  }

  @override
  Widget build(BuildContext context) {
    final primaryColor = Theme.of(context).primaryColor;
    final borderLight = Colors.grey.shade200;
    final voiceActive = _isAnyVoiceActive;
    final voiceLoading = kIsWeb && _isTranscribing;

    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text('AgriAI Assistant'),
        actions: [
          TextButton.icon(
            onPressed: _showLocalePicker,
            icon: Icon(Icons.language, size: 18, color: Colors.grey.shade700),
            label: Text(
              '$_currentLanguageLabel reply',
              style:
                  TextStyle(fontSize: 12, color: Colors.grey.shade700),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              reverse: true,
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              itemCount: messages.length + (_isResponding ? 1 : 0),
              itemBuilder: (context, index) {
                if (_isResponding && index == 0) {
                  return Align(
                    alignment: Alignment.centerLeft,
                    child: Container(
                      margin: const EdgeInsets.only(bottom: 16),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 12),
                      decoration: BoxDecoration(
                          color: const Color(0xFFF1F3F5),
                          borderRadius: BorderRadius.circular(8)),
                      child: SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation<Color>(
                                primaryColor)),
                      ),
                    ),
                  );
                }

                final msgIndex = messages.length - 1 - (_isResponding ? index - 1 : index);
                final msg = messages[msgIndex];
                final isUser = msg['isUser'] as bool;
                final isError = msg['isError'] == true;
                return Align(
                  alignment:
                      isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 16),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 12),
                    decoration: BoxDecoration(
                      color: isError
                          ? const Color(0xFFFFF2F2)
                          : (isUser ? primaryColor : const Color(0xFFF1F3F5)),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    constraints: BoxConstraints(
                        maxWidth: MediaQuery.of(context).size.width * 0.75),
                    child: SelectableText(
                      msg['text'] as String,
                      style: TextStyle(
                          color: isError
                              ? const Color(0xFF8A0000)
                              : isUser
                              ? Colors.white
                              : const Color(0xFF1C1E21),
                          fontSize: 14,
                          height: 1.4,
                          fontFamilyFallback: AppTheme.multilingualFontFallback),
                    ),
                  ),
                );
              },
            ),
          ),
          Container(
            padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
            decoration: BoxDecoration(
                color: const Color(0xFFF8F9FA),
                border: Border(top: BorderSide(color: borderLight))),
            child: SafeArea(
              top: false,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (voiceActive || voiceLoading)
                    Container(
                      margin: const EdgeInsets.only(bottom: 10),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 10),
                      decoration: BoxDecoration(
                        color: voiceLoading
                            ? Colors.orange.shade50
                            : Colors.red.shade50,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                            color: voiceLoading
                                ? Colors.orange.shade200
                                : Colors.red.shade200),
                      ),
                      child: Row(
                        children: [
                          AnimatedBuilder(
                            animation: _pulseAnimation,
                            builder: (context, child) => Transform.scale(
                              scale: _pulseAnimation.value,
                              child: child,
                            ),
                            child: Container(
                              width: 10,
                              height: 10,
                              decoration: BoxDecoration(
                                  color: voiceLoading
                                      ? Colors.orange
                                      : Colors.red,
                                  shape: BoxShape.circle),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              voiceLoading
                                  ? 'Transcribing...'
                                  : (kIsWeb
                                      ? 'Listening... auto-stops when you stop speaking'
                                      : (_lastWords.isEmpty
                                          ? 'Listening... Speak now'
                                          : _lastWords)),
                              style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: (voiceLoading || kIsWeb) ? FontWeight.w600 : FontWeight.normal,
                                  color: voiceLoading
                                      ? Colors.orange.shade700
                                      : Colors.red.shade700,
                                  fontStyle: (_lastWords.isEmpty && !voiceLoading && !kIsWeb)
                                      ? FontStyle.italic
                                      : FontStyle.normal),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          if (!voiceLoading) ...[
                            const SizedBox(width: 8),
                            MouseRegion(
                              cursor: SystemMouseCursors.click,
                              child: GestureDetector(
                                onTap: _toggleVoice,
                                child: Icon(Icons.stop_circle,
                                    color: Colors.red.shade600, size: 28),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      MouseRegion(
                        cursor: SystemMouseCursors.click,
                        child: GestureDetector(
                          onTap: voiceLoading ? null : _toggleVoice,
                          child: AnimatedBuilder(
                            animation: _pulseAnimation,
                            builder: (context, child) => Container(
                              width: 48,
                              height: 48,
                              decoration: BoxDecoration(
                                color: voiceActive
                                    ? Colors.red
                                    : (voiceLoading
                                        ? Colors.orange
                                        : primaryColor),
                                shape: BoxShape.circle,
                                boxShadow: voiceActive
                                    ? [
                                        BoxShadow(
                                            color: Colors.red
                                                .withValues(alpha: 0.3),
                                            blurRadius:
                                                8 * _pulseAnimation.value,
                                            spreadRadius:
                                                2 * _pulseAnimation.value)
                                      ]
                                    : null,
                              ),
                              child: Icon(
                                voiceActive ? Icons.stop : Icons.mic,
                                color: Colors.white,
                                size: 22,
                              ),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: TextField(
                          controller: _controller,
                          style: const TextStyle(fontSize: 14),
                          maxLines: null,
                          textInputAction: TextInputAction.send,
                          onSubmitted: (_) => _sendMessage(),
                          decoration: InputDecoration(
                            hintText: voiceActive
                                ? (kIsWeb
                                    ? 'Recording...'
                                    : 'Listening...')
                                : 'Ask about crops, diseases, weather...',
                            fillColor: Colors.white,
                            filled: true,
                            contentPadding: const EdgeInsets.symmetric(
                                horizontal: 16, vertical: 12),
                            border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(24),
                                borderSide:
                                    BorderSide(color: borderLight)),
                            enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(24),
                                borderSide:
                                    BorderSide(color: borderLight)),
                            focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(24),
                                borderSide:
                                    BorderSide(color: primaryColor)),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      MouseRegion(
                        cursor: SystemMouseCursors.click,
                        child: GestureDetector(
                          onTap: _isResponding ? null : _sendMessage,
                          child: Container(
                            width: 48,
                            height: 48,
                            decoration: BoxDecoration(
                              color: _isResponding
                                  ? Colors.grey.shade300
                                  : primaryColor,
                              shape: BoxShape.circle,
                            ),
                            child: const Icon(Icons.arrow_upward,
                                color: Colors.white, size: 20),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
