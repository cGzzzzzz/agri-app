import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../services/api_service.dart';
import '../../../services/auth_service.dart';

class AssistantScreen extends StatefulWidget {
  const AssistantScreen({super.key});

  @override
  State<AssistantScreen> createState() => _AssistantScreenState();
}

class _AssistantScreenState extends State<AssistantScreen> {
  final List<Map<String, dynamic>> messages = [];
  final TextEditingController _controller = TextEditingController();
  bool _isResponding = false;
  bool _historyLoaded = false;

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    final auth = Provider.of<AuthService>(context, listen: false);
    final api = ApiService(auth);
    final history = await api.getChatHistory();
    if (mounted && history.isNotEmpty) {
      setState(() {
        for (final h in history.reversed) {
          messages.add({'text': h['question'] ?? h['message'] ?? '', 'isUser': true});
          messages.add({'text': h['response'] ?? '', 'isUser': false});
        }
        _historyLoaded = true;
      });
    }
    if (!_historyLoaded && mounted) {
      final userName = auth.user?.name ?? 'Farmer';
      setState(() {
        messages.add({
          'text': 'Hello $userName! I can help with crop diseases, weather, and farm management. How can I assist you today?',
          'isUser': false,
        });
        _historyLoaded = true;
      });
    }
  }

  Future<void> _sendMessage() async {
    final query = _controller.text.trim();
    if (query.isEmpty) return;

    setState(() {
      messages.add({'text': query, 'isUser': true});
      _isResponding = true;
      _controller.clear();
    });

    final auth = Provider.of<AuthService>(context, listen: false);
    final api = ApiService(auth);
    final response = await api.sendMessage(query);

    if (mounted) {
      setState(() {
        messages.add({'text': response, 'isUser': false});
        _isResponding = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final primaryColor = Theme.of(context).primaryColor;
    final borderLight = Colors.grey.shade200;

    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(title: const Text('AgriAI Assistant')),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              itemCount: messages.length + (_isResponding ? 1 : 0),
              itemBuilder: (context, index) {
                if (index == messages.length) {
                  return Align(
                    alignment: Alignment.centerLeft,
                    child: Container(
                      margin: const EdgeInsets.only(bottom: 16),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      decoration: BoxDecoration(color: const Color(0xFFF1F3F5), borderRadius: BorderRadius.circular(8)),
                      child: SizedBox(
                        width: 16, height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2, valueColor: AlwaysStoppedAnimation<Color>(primaryColor)),
                      ),
                    ),
                  );
                }
                final msg = messages[index];
                final isUser = msg['isUser'] as bool;
                return Align(
                  alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 16),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    decoration: BoxDecoration(
                      color: isUser ? primaryColor : const Color(0xFFF1F3F5),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
                    child: Text(
                      msg['text'] as String,
                      style: TextStyle(color: isUser ? Colors.white : const Color(0xFF1C1E21), fontSize: 14, height: 1.4),
                    ),
                  ),
                );
              },
            ),
          ),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: const Color(0xFFF8F9FA), border: Border(top: BorderSide(color: borderLight))),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    style: const TextStyle(fontSize: 14),
                    onSubmitted: (_) => _sendMessage(),
                    decoration: InputDecoration(
                      hintText: 'Ask about crops, diseases, weather...',
                      fillColor: Colors.white,
                      filled: true,
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: borderLight)),
                      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: borderLight)),
                      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: primaryColor)),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                SizedBox(
                  height: 48,
                  child: ElevatedButton(
                    onPressed: _isResponding ? null : _sendMessage,
                    style: ElevatedButton.styleFrom(shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)), padding: const EdgeInsets.symmetric(horizontal: 16)),
                    child: const Icon(Icons.arrow_upward, size: 20),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
