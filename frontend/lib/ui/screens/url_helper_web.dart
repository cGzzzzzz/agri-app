import 'dart:js_interop';

import 'package:web/web.dart' as web;

String getUrlHashImpl() {
  final hash = web.window.location.hash;
  return hash.startsWith('#') ? hash.substring(1) : hash;
}

void setUrlHashImpl(String hash) {
  web.window.location.hash = hash;
}

String getHashEarlyImpl() {
  final hash = web.window.location.hash;
  return hash.startsWith('#') ? hash.substring(1) : hash;
}

void listenHashChangeImpl(void Function(String hash) onChange) {
  web.window.addEventListener('hashchange', ((web.Event _) {
    final hash = web.window.location.hash;
    final value = hash.startsWith('#') ? hash.substring(1) : hash;
    onChange(value);
  }).toJS);
}
