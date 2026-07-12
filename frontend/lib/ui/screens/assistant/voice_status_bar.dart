import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

class VoiceStatusBar extends StatelessWidget {
  final bool voiceActive;
  final bool voiceLoading;
  final String lastWords;
  final Animation<double> pulseAnimation;
  final VoidCallback onToggleVoice;

  const VoiceStatusBar({
    super.key,
    required this.voiceActive,
    required this.voiceLoading,
    required this.lastWords,
    required this.pulseAnimation,
    required this.onToggleVoice,
  });

  @override
  Widget build(BuildContext context) {
    if (!voiceActive && !voiceLoading) return const SizedBox.shrink();

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: voiceLoading ? Colors.orange.shade50 : Colors.red.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
            color: voiceLoading
                ? Colors.orange.shade200
                : Colors.red.shade200),
      ),
      child: Row(
        children: [
          AnimatedBuilder(
            animation: pulseAnimation,
            builder: (context, child) => Transform.scale(
              scale: pulseAnimation.value,
              child: child,
            ),
            child: Container(
              width: 10,
              height: 10,
              decoration: BoxDecoration(
                  color: voiceLoading ? Colors.orange : Colors.red,
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
                      : (lastWords.isEmpty
                          ? 'Listening... Speak now'
                          : lastWords)),
              style: TextStyle(
                  fontSize: 13,
                  fontWeight:
                      (voiceLoading || kIsWeb) ? FontWeight.w600 : FontWeight.normal,
                  color: voiceLoading
                      ? Colors.orange.shade700
                      : Colors.red.shade700,
                  fontStyle: (lastWords.isEmpty && !voiceLoading && !kIsWeb)
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
                onTap: onToggleVoice,
                child: Icon(Icons.stop_circle,
                    color: Colors.red.shade600, size: 28),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
