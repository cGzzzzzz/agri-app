import 'url_helper_stub.dart'
    if (dart.library.js_interop) 'url_helper_web.dart';

String getUrlHash() => getUrlHashImpl();
void setUrlHash(String hash) => setUrlHashImpl(hash);
String getHashEarly() => getHashEarlyImpl();
void listenHashChange(void Function(String hash) onChange) => listenHashChangeImpl(onChange);
