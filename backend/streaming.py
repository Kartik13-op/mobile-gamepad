"""Low-latency desktop screen streaming for the mobile controller.

The stream is deliberately opt-in.  The monitor enables it and phones only
receive frames after completing a WebRTC offer against the local mobile
server.
"""

from __future__ import annotations

import asyncio
import ctypes
import logging
import time
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

logger = logging.getLogger(__name__)

try:
    from aiortc import AudioStreamTrack, VideoStreamTrack
except ImportError:  # Keep the controller usable until optional stream deps are installed.
    class AudioStreamTrack:  # type: ignore[no-redef]
        readyState = "live"

        def stop(self) -> None:
            self.readyState = "ended"

    class VideoStreamTrack:  # type: ignore[no-redef]
        readyState = "live"

        def stop(self) -> None:
            self.readyState = "ended"


@dataclass
class StreamSettings:
    """User-selectable screen stream settings."""

    width: int = 1280
    height: int = 720
    fps: int = 30
    quality: str = "balanced"

    def as_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "quality": self.quality,
        }


class ScreenVideoTrack(VideoStreamTrack):
    """An aiortc-compatible VideoStreamTrack backed by the primary display."""

    kind = "video"

    def __init__(self, manager: "StreamManager") -> None:
        super().__init__()
        self._manager = manager
        self._capture = None
        self._last_frame_at = 0.0
        self._cursor_patch = self._build_cursor_patch()

    def stop(self) -> None:
        if self._capture is not None:
            self._capture.close()
            self._capture = None
        super().stop()

    async def recv(self):
        from av import VideoFrame
        import numpy as np
        from PIL import Image

        settings = self._manager.settings
        interval = 1.0 / max(1, settings.fps)
        wait_for = interval - (time.monotonic() - self._last_frame_at)
        if wait_for > 0:
            await asyncio.sleep(wait_for)
        self._last_frame_at = time.monotonic()

        if self._capture is None:
            import mss

            self._capture = mss.mss()

        monitor = self._capture.monitors[1]
        raw = self._capture.grab(monitor)
        frame = np.asarray(raw)[:, :, :3]  # mss returns BGRA; aiortc accepts BGR.
        frame = self._draw_cursor(frame, monitor, self._cursor_patch)
        target = (settings.width, settings.height)
        if target[0] > 0 and target[1] > 0 and frame.shape[1::-1] != target:
            resampling = {
                "economy": Image.Resampling.BILINEAR,
                # BILINEAR keeps the balanced path responsive; WebRTC handles
                # compression, so spending CPU on a sharper resize only adds delay.
                "balanced": Image.Resampling.BILINEAR,
                "high": Image.Resampling.LANCZOS,
            }.get(settings.quality, Image.Resampling.BICUBIC)
            frame = np.asarray(Image.fromarray(frame).resize(target, resampling))

        video = VideoFrame.from_ndarray(frame, format="bgr24")
        # Use the same monotonic stream clock as audio.  Independent counters
        # make a newly connected phone start with an arbitrary A/V offset.
        video.pts = max(0, int((time.monotonic() - self._manager.clock_start) * 90000))
        video.time_base = Fraction(1, 90000)
        return video

    @staticmethod
    def _build_cursor_patch():
        """Build the pointer once; compositing a small array is much cheaper per frame."""
        try:
            import numpy as np
            from PIL import Image, ImageDraw

            image = Image.new("RGBA", (24, 31), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            pointer = [(0, 0), (2, 22), (8, 17), (14, 29), (19, 26), (13, 14), (22, 13)]
            draw.polygon(pointer, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=2)
            patch = np.asarray(image)
            return patch[:, :, :3][:, :, ::-1], patch[:, :, 3] > 0
        except Exception:
            return None, None

    @staticmethod
    def _cursor_position() -> tuple[int, int] | None:
        """Read the Windows cursor without invoking the slower screenshot path."""
        try:
            from ctypes import wintypes
            point = wintypes.POINT()
            if ctypes.windll.user32.GetCursorPos(ctypes.byref(point)):
                return point.x, point.y
        except Exception:
            pass
        try:
            import pyautogui
            return pyautogui.position()
        except Exception:
            return None

    @classmethod
    def _draw_cursor(cls, frame, monitor, cursor_patch):
        """Composite a high-contrast pointer because mss does not capture cursors."""
        patch, mask = cursor_patch
        position = cls._cursor_position()
        if patch is None or mask is None or position is None:
            return frame

        x = position[0] - int(monitor["left"])
        y = position[1] - int(monitor["top"])
        height, width = frame.shape[:2]
        if x >= width or y >= height or x + patch.shape[1] <= 0 or y + patch.shape[0] <= 0:
            return frame

        left, top = max(0, x), max(0, y)
        right, bottom = min(width, x + patch.shape[1]), min(height, y + patch.shape[0])
        patch_left, patch_top = left - x, top - y
        patch_right, patch_bottom = patch_left + (right - left), patch_top + (bottom - top)
        visible = mask[patch_top:patch_bottom, patch_left:patch_right]
        frame[top:bottom, left:right][visible] = patch[patch_top:patch_bottom, patch_left:patch_right][visible]
        return frame


class StreamManager:
    """Own stream settings and the currently connected WebRTC peers."""

    def __init__(self) -> None:
        self.settings = StreamSettings()
        self.active = False
        self._peer_connections: set[Any] = set()
        self.clock_start = time.monotonic()

    @staticmethod
    def _int_setting(value: Any, allowed: set[int], fallback: int) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return fallback
        return number if number in allowed else fallback

    def update_settings(self, data: dict[str, Any]) -> dict[str, Any]:
        width = self._int_setting(data.get("width"), {0, 960, 1280, 1920}, self.settings.width)
        height = self._int_setting(data.get("height"), {0, 540, 720, 1080}, self.settings.height)
        fps = self._int_setting(data.get("fps"), {15, 24, 30, 60}, self.settings.fps)
        quality = str(data.get("quality", self.settings.quality))
        if quality not in {"economy", "balanced", "high"}:
            quality = self.settings.quality
        self.settings = StreamSettings(width, height, fps, quality)
        return self.settings.as_dict()

    def status(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "settings": self.settings.as_dict(),
            "peers": len(self._peer_connections),
            "available": self._dependencies_available(),
            "audio_available": self._audio_dependencies_available(),
        }

    @staticmethod
    def _dependencies_available() -> bool:
        try:
            import aiortc  # noqa: F401
            import mss  # noqa: F401
            import numpy  # noqa: F401
            import PIL  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def _audio_dependencies_available() -> bool:
        try:
            import soundcard  # noqa: F401 - Windows WASAPI loopback
            import numpy  # noqa: F401
            return True
        except ImportError:
            return False

    def start(self) -> dict[str, Any]:
        self.active = True
        self.clock_start = time.monotonic()
        return self.status()

    async def stop(self) -> dict[str, Any]:
        self.active = False
        peers = list(self._peer_connections)
        self._peer_connections.clear()
        for peer in peers:
            try:
                await peer.close()
            except Exception:
                logger.debug("WebRTC peer close failed", exc_info=True)
        return self.status()

    async def create_answer(self, offer: dict[str, Any]) -> dict[str, Any]:
        if not self.active:
            raise RuntimeError("Screen streaming is not enabled")
        if not self._dependencies_available():
            raise RuntimeError("Screen streaming dependencies are not installed")

        from aiortc import RTCPeerConnection, RTCSessionDescription, RTCRtpSender

        peer = RTCPeerConnection()
        self._peer_connections.add(peer)
        track = ScreenVideoTrack(self)
        peer.addTrack(track)
        audio_track = None
        if self._audio_dependencies_available():
            audio_track = DesktopAudioTrack(self)
            peer.addTrack(audio_track)

        @peer.on("connectionstatechange")
        async def on_connectionstatechange() -> None:
            if peer.connectionState in {"failed", "closed", "disconnected"}:
                self._peer_connections.discard(peer)
                track.stop()
                if audio_track is not None:
                    audio_track.stop()
                await peer.close()

        await peer.setRemoteDescription(
            RTCSessionDescription(sdp=str(offer.get("sdp", "")), type=str(offer.get("type", "offer")))
        )
        # Prefer VP8 for mobile compatibility. It is broadly available in
        # browser hardware/software decoders and avoids black video on phones
        # that advertise H.264 but cannot decode the negotiated profile.
        for transceiver in peer.getTransceivers():
            if transceiver.kind != "video" or not hasattr(transceiver, "setCodecPreferences"):
                continue
            codecs = RTCRtpSender.getCapabilities("video").codecs
            vp8 = [codec for codec in codecs if codec.name.upper() == "VP8"]
            if vp8:
                transceiver.setCodecPreferences(vp8 + [codec for codec in codecs if codec not in vp8])
        answer = await peer.createAnswer()
        await peer.setLocalDescription(answer)
        return {"sdp": peer.localDescription.sdp, "type": peer.localDescription.type}


class DesktopAudioTrack(AudioStreamTrack):
    """Low-latency Windows speaker loopback track, clocked with the video."""

    kind = "audio"

    def __init__(self, manager: "StreamManager") -> None:
        super().__init__()
        self._manager = manager
        self._recorder = None
        self._sample_count = 0
        self._sample_rate = 48000
        self._channels = 2

    def stop(self) -> None:
        if self._recorder is not None:
            try:
                self._recorder.__exit__(None, None, None)
            except Exception:
                logger.debug("Audio recorder close failed", exc_info=True)
            self._recorder = None
        super().stop()

    async def recv(self):
        import numpy as np
        from av import AudioFrame

        if self._recorder is None:
            import soundcard as sc
            speaker = sc.default_speaker()
            # SoundCard exposes loopback capture through a microphone object
            # associated with the current speaker, not on the Speaker itself.
            loopback = sc.get_microphone(speaker.id, include_loopback=True)
            self._recorder = loopback.recorder(
                samplerate=self._sample_rate,
                channels=self._channels,
                blocksize=960,
            )
            self._recorder.__enter__()

        # Keep capture off the asyncio event loop; WASAPI can occasionally
        # block while a device changes state.
        samples = await asyncio.to_thread(self._recorder.record, numframes=960)
        samples = np.asarray(samples, dtype=np.float32)
        if samples.ndim == 1:
            samples = np.repeat(samples[:, None], self._channels, axis=1)
        samples = np.clip(samples, -1.0, 1.0)
        # ``fltp`` is planar float audio: one row per channel, which matches
        # SoundCard's interleaved input after the transpose and avoids an
        # implicit channel reshape in PyAV.
        frame = AudioFrame.from_ndarray(np.ascontiguousarray(samples.T), format="fltp", layout="stereo")
        frame.sample_rate = self._sample_rate
        frame.pts = max(
            self._sample_count,
            int((time.monotonic() - self._manager.clock_start) * self._sample_rate),
        )
        frame.time_base = Fraction(1, self._sample_rate)
        self._sample_count = frame.pts + samples.shape[0]
        return frame


stream_manager = StreamManager()
