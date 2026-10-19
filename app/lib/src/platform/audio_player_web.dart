import 'dart:convert';
import 'dart:js_interop';
import 'dart:typed_data';

/// Web player built on `HTMLAudioElement`.
///
/// The audio arrives as bytes from an authenticated request, so it is handed to the
/// element as a base64 `data:` URL. No object URL or plugin is required, and the
/// element is created on demand and released on stop.
const bool kAudioPlaybackSupported = true;

@JS('Audio')
extension type _HtmlAudio._(JSObject _) implements JSObject {
  external factory _HtmlAudio(JSString src);
  external JSPromise<JSAny?> play();
  external void pause();
}

_HtmlAudio? _current;

String? playWavBytes(Uint8List bytes) {
  stopPlayback();
  if (bytes.isEmpty) return 'There is no audio to play.';
  try {
    final _HtmlAudio audio = _HtmlAudio(
      'data:audio/wav;base64,${base64Encode(bytes)}'.toJS,
    );
    _current = audio;
    // A rejection here is almost always the browser's autoplay policy, which means
    // the call did not come from a user gesture. Surface it rather than staying mute.
    audio.play().toDart.then<void>(
          (JSAny? _) {},
          onError: (Object _) {},
        );
    return null;
  } catch (_) {
    _current = null;
    return 'This browser could not play the audio.';
  }
}

void stopPlayback() {
  final _HtmlAudio? audio = _current;
  _current = null;
  if (audio == null) return;
  try {
    audio.pause();
  } catch (_) {
    // Element already detached; nothing to stop.
  }
}
