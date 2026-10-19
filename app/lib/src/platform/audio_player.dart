/// Plays back WAV audio, without pulling in a plugin.
///
/// Only the web build ships a real player (`HTMLAudioElement` via `dart:js_interop`);
/// every other target resolves to a stub that reports playback as unsupported, so the
/// app still analyzes, tests and compiles on the VM.
library;

export 'audio_player_stub.dart'
    if (dart.library.js_interop) 'audio_player_web.dart';
