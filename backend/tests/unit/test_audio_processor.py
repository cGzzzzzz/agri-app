import struct

import numpy as np

from app.stt.audio_processor import (
    _float32_to_wav,
    _noise_gate,
    _peak_normalize,
    _trim_silence,
    preprocess_audio,
)


def _make_sine_pcm16(
    duration_s: float = 1.0, sample_rate: int = 48000, freq: float = 440.0
) -> bytes:
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    audio = (0.8 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    pcm16 = (audio * 32767).astype(np.int16)
    return pcm16.tobytes()


def _make_silence_pcm16(duration_s: float = 1.0, sample_rate: int = 48000) -> bytes:
    n = int(sample_rate * duration_s)
    return np.zeros(n, dtype=np.int16).tobytes()


def _make_noisy_pcm16(duration_s: float = 1.0, sample_rate: int = 48000) -> bytes:
    rng = np.random.default_rng(42)
    audio = rng.uniform(-0.3, 0.3, int(sample_rate * duration_s)).astype(np.float32)
    pcm16 = (audio * 32767).astype(np.int16)
    return pcm16.tobytes()


class TestTrimSilence:
    def test_all_silence_returns_full_array(self):
        audio = np.zeros(48000, dtype=np.float32)
        result = _trim_silence(audio, threshold_db=-40.0, sample_rate=48000)
        assert len(result) == 48000

    def test_no_silence_returns_full(self):
        audio = np.ones(48000, dtype=np.float32) * 0.5
        result = _trim_silence(audio, threshold_db=-40.0, sample_rate=48000)
        assert len(result) >= 47000

    def test_leading_trailing_silence_trimmed(self):
        speech = np.ones(40000, dtype=np.float32) * 0.5
        silence = np.zeros(20000, dtype=np.float32)
        audio = np.concatenate([silence, speech, silence])
        result = _trim_silence(audio, threshold_db=-40.0, sample_rate=48000, padding_ms=20)
        assert len(result) < len(audio)
        assert len(result) > 30000

    def test_padding_preserved(self):
        speech = np.ones(5000, dtype=np.float32) * 0.5
        audio = np.concatenate(
            [np.zeros(5000, dtype=np.float32), speech, np.zeros(5000, dtype=np.float32)]
        )
        result = _trim_silence(audio, threshold_db=-40.0, sample_rate=48000, padding_ms=200)
        assert len(result) > 5000


class TestPeakNormalize:
    def test_normalizes_loud_audio(self):
        audio = np.ones(1000, dtype=np.float32) * 0.9
        result = _peak_normalize(audio, target_db=-3.0)
        peak = float(np.max(np.abs(result)))
        assert peak < 1.0
        assert peak > 0.3

    def test_normalizes_quiet_audio(self):
        audio = np.ones(1000, dtype=np.float32) * 0.01
        result = _peak_normalize(audio, target_db=-3.0)
        peak = float(np.max(np.abs(result)))
        assert peak > 0.3

    def test_silence_noop(self):
        audio = np.zeros(1000, dtype=np.float32)
        result = _peak_normalize(audio, target_db=-3.0)
        assert np.all(result == 0.0)


class TestNoiseGate:
    def test_clips_below_threshold(self):
        audio = np.array([0.001, 0.5, -0.001, 0.8], dtype=np.float32)
        result = _noise_gate(audio, threshold=0.005)
        assert result[0] == 0.0
        assert result[1] == 0.5
        assert result[2] == 0.0
        assert result[3] == 0.8

    def test_preserves_above_threshold(self):
        audio = np.array([0.1, -0.2, 0.3], dtype=np.float32)
        result = _noise_gate(audio, threshold=0.005)
        np.testing.assert_array_equal(result, audio)


class TestFloat32ToWav:
    def test_wav_starts_with_riff(self):
        audio = np.zeros(100, dtype=np.float32)
        wav = _float32_to_wav(audio, 16000)
        assert wav[:4] == b"RIFF"
        assert wav[8:12] == b"WAVE"
        assert wav[12:16] == b"fmt "
        assert wav[36:40] == b"data"

    def test_wav_header_fields(self):
        audio = np.zeros(100, dtype=np.float32)
        wav = _float32_to_wav(audio, 16000)
        assert len(wav) == 44 + 200
        num_channels = struct.unpack_from("<H", wav, 22)[0]
        sample_rate = struct.unpack_from("<I", wav, 24)[0]
        assert num_channels == 1
        assert sample_rate == 16000


class TestPreprocessAudio:
    def test_full_pipeline_valid_wav(self):
        pcm = _make_sine_pcm16(1.0, 48000, 440.0)
        wav = preprocess_audio(pcm, sample_rate_in=48000, channels=1)
        assert wav[:4] == b"RIFF"
        assert wav[8:12] == b"WAVE"

    def test_resamples_48k_to_16k(self):
        pcm = _make_sine_pcm16(1.0, 48000, 440.0)
        wav = preprocess_audio(pcm, sample_rate_in=48000, channels=1, sample_rate_out=16000)
        data_size = struct.unpack_from("<I", wav, 40)[0]
        expected_samples = 16000
        assert abs(data_size - expected_samples * 2) < 100

    def test_all_silence_produces_valid_wav(self):
        pcm = _make_silence_pcm16(1.0, 48000)
        wav = preprocess_audio(pcm, sample_rate_in=48000, channels=1)
        assert wav[:4] == b"RIFF"
        assert wav[8:12] == b"WAVE"

    def test_stereo_takes_first_channel(self):
        pcm_mono = _make_sine_pcm16(0.5, 48000, 440.0)
        samples = np.frombuffer(pcm_mono, dtype=np.int16)
        stereo = np.column_stack([samples, samples]).flatten().tobytes()
        wav = preprocess_audio(stereo, sample_rate_in=48000, channels=2)
        assert wav[:4] == b"RIFF"
