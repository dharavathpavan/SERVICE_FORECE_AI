import 'dart:typed_data';

/// Non-web stub: the browser is the only target with an audio element here.
const bool kAudioPlaybackSupported = false;

String? playWavBytes(Uint8List bytes) =>
    'Audio playback is available in the web app only.';

void stopPlayback() {}
