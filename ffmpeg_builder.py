"""Safe Phase 2 FFmpeg command construction for a two-input duet.

The builder returns argv arrays, never shell command strings. It supports video
trimming, canvas normalization, side-by-side composition, positive audio sync
delays, gain/mute, and inputs without an audio stream.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class InputSpec:
    path: Path
    trim_start_ms: int = 0
    trim_end_ms: Optional[int] = None
    sync_offset_ms: int = 0
    gain: float = 1.0
    muted: bool = False
    has_audio: bool = True


def _seconds(ms: int) -> str:
    if ms < 0:
        raise ValueError("time values cannot be negative")
    return f"{ms / 1000:.3f}"


def _duration(spec: InputSpec) -> Optional[str]:
    if spec.trim_end_ms is None:
        return None
    return _seconds(spec.trim_end_ms - spec.trim_start_ms)


def _audio_chain(index: int, spec: InputSpec) -> str:
    start = _seconds(spec.trim_start_ms)
    end = f":end={_seconds(spec.trim_end_ms)}" if spec.trim_end_ms is not None else ""
    if spec.has_audio:
        chain = f"[{index}:a]atrim=start={start}{end},asetpts=PTS-STARTPTS"
    else:
        # An infinite silent source is safe because the final -shortest flag
        # terminates it at the composed video's duration.
        chain = "anullsrc=channel_layout=stereo:sample_rate=48000"
        duration = _duration(spec)
        if duration is not None:
            chain += f",atrim=duration={duration}"
    chain += ",aresample=async=1:first_pts=0"
    if spec.sync_offset_ms > 0:
        delay = spec.sync_offset_ms
        chain += f",adelay={delay}|{delay}"
    elif spec.sync_offset_ms < 0:
        # A negative offset advances audio by removing its leading portion.
        advance = _seconds(abs(spec.sync_offset_ms))
        chain += f",atrim=start={advance},asetpts=PTS-STARTPTS"
    chain += f",volume={0.0 if spec.muted else spec.gain:g},aresample=48000[a{index}]"
    return chain


def build_split_screen_command(
    inputs: list[InputSpec],
    output: Path,
    *,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    crf: int = 20,
    preset: str = "medium",
) -> list[str]:
    """Build a deterministic two-input split-screen FFmpeg command.

    Filter graph:
      each video: trim -> setpts -> scale/pad -> fps -> setsar
      each audio: atrim/anullsrc -> timestamp reset -> sync -> volume -> resample
      video: [v0][v1]hstack
      audio: [a0][a1]amix
    """
    if len(inputs) != 2:
        raise ValueError("exactly two inputs are required")
    if width <= 0 or height <= 0 or fps <= 0:
        raise ValueError("canvas dimensions and fps must be positive")
    if width % 2:
        raise ValueError("width must be even for side-by-side output")
    if not 0 <= crf <= 51:
        raise ValueError("crf must be between 0 and 51")
    if not output.parent.exists():
        raise FileNotFoundError(f"output directory does not exist: {output.parent}")

    half_width = width // 2
    graph: list[str] = []
    for i, spec in enumerate(inputs):
        if not spec.path.is_file():
            raise FileNotFoundError(str(spec.path))
        if spec.trim_start_ms < 0:
            raise ValueError("trim_start_ms cannot be negative")
        if spec.trim_end_ms is not None and spec.trim_end_ms <= spec.trim_start_ms:
            raise ValueError("trim_end_ms must be greater than trim_start_ms")
        if spec.gain < 0:
            raise ValueError("gain cannot be negative")
        start = _seconds(spec.trim_start_ms)
        end = f":end={_seconds(spec.trim_end_ms)}" if spec.trim_end_ms is not None else ""
        graph.append(
            f"[{i}:v]trim=start={start}{end},setpts=PTS-STARTPTS,"
            f"scale={half_width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={half_width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"fps={fps},setsar=1[v{i}]"
        )
        graph.append(_audio_chain(i, spec))

    graph.append("[v0][v1]hstack=inputs=2:shortest=0[vout]")
    graph.append("[a0][a1]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[aout]")
    filter_complex = ";".join(graph)

    return [
        "ffmpeg", "-hide_banner", "-nostdin", "-y",
        "-i", str(inputs[0].path), "-i", str(inputs[1].path),
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-shortest", str(output),
    ]


def build_tiktok_duet_command(
    inputs: list[InputSpec],
    output: Path,
    *,
    fps: int = 30,
    crf: int = 20,
    preset: str = "medium",
) -> list[str]:
    """Build a TikTok-oriented vertical duet export.

    The output is 1080x1920 with a side-by-side duet layout, H.264 video,
    AAC audio, yuv420p, and fast-start MP4 metadata. Attribution is carried
    in the companion credit packet; this function never posts externally.
    """
    return build_split_screen_command(
        inputs,
        output,
        width=1080,
        height=1920,
        fps=fps,
        crf=crf,
        preset=preset,
    )
