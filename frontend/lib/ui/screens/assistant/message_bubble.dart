import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';

class MessageBubble extends StatelessWidget {
  final String text;
  final bool isUser;
  final bool isError;

  const MessageBubble({
    super.key,
    required this.text,
    required this.isUser,
    this.isError = false,
  });

  @override
  Widget build(BuildContext context) {
    final primaryColor = Theme.of(context).primaryColor;
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 16),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: isError
              ? const Color(0xFFFFF2F2)
              : (isUser ? primaryColor : const Color(0xFFF1F3F5)),
          borderRadius: BorderRadius.circular(8),
        ),
        constraints: BoxConstraints(
            maxWidth: MediaQuery.of(context).size.width * 0.75),
        child: SelectableText(
          text,
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
  }
}
