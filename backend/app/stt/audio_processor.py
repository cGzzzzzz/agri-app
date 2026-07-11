import struct

import numpy as np
from scipy import signal as scipy_signal


def preprocess_audio(
    pcm16_bytes: bytes,
    sample_rate_in: int = 48000,
    channels: int = 1,
    silence_threshold_db: float = -40.0,
    target_peak_db: float = -3.0,
    sample_rate_out: int = 16000,
) -> bytes:
    audio = np.frombuffer(pcm16_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    if channels > 1:
        audio = audio.reshape(-1, channels)[:, 0]

    audio = _trim_silence(audio, silence_threshold_db, sample_rate_in)
    if len(audio) == 0:
        raise ValueError("Audio is all silence")

    audio = _peak_normalize(audio, target_peak_db)
    audio = _noise_gate(audio)

    if sample_rate_in != sample_rate_out:
        ratio_gcd = int(np.gcd(sample_rate_out, sample_rate_in))
        up = sample_rate_out // ratio_gcd
        down = sample_rate_in // ratio_gcd
        audio = scipy_signal.resample_poly(audio, up=up, down=down).astype(np.float32)

    return _float32_to_wav(audio, sample_rate_out)


def _trim_silence(
    audio: np.ndarray,
    threshold_db: float = -40.0,
    sample_rate: int = 48000,
    chunk_ms: int = 20,
    padding_ms: int = 200,
) -> np.ndarray:
    samples_per_chunk = max(1, int(sample_rate * chunk_ms / 1000))
    padding_samples = int(sample_rate * padding_ms / 1000)
    threshold_linear = 10 ** (threshold_db / 20.0)

    start = 0
    for i in range(0, len(audio) - samples_per_chunk, samples_per_chunk):
        chunk = audio[i : i + samples_per_chunk]
        rms = float(np.sqrt(np.mean(chunk**2)))
        if rms > threshold_linear:
            start = max(0, i - padding_samples)
            break

    end = len(audio)
    for i in range(len(audio) - samples_per_chunk, 0, -samples_per_chunk):
        chunk = audio[i : i + samples_per_chunk]
        rms = float(np.sqrt(np.mean(chunk**2)))
        if rms > threshold_linear:
            end = min(len(audio), i + samples_per_chunk + padding_samples)
            break

    return audio[start:end]


def _peak_normalize(audio: np.ndarray, target_db: float = -3.0) -> np.ndarray:
    peak = float(np.max(np.abs(audio)))
    if peak < 1e-10:
        return audio
    target_linear = 10 ** (target_db / 20.0)
    gain = target_linear / peak
    return np.clip(audio * gain, -1.0, 1.0)


def _noise_gate(audio: np.ndarray, threshold: float = 0.005) -> np.ndarray:
    return np.where(np.abs(audio) < threshold, 0.0, audio)


def _float32_to_wav(audio: np.ndarray, sample_rate: int) -> bytes:
    pcm16 = (audio * 32767).astype(np.int16)
    raw_data = pcm16.tobytes()

    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = len(raw_data)

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )

    return header + raw_data
