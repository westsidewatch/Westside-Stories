"""Local subtitle burn-in style profiles for Westside Stories 1.1.

Styling is deliberately independent from transcription and Doré. SRT remains
plain, portable text; visual choices are applied only during optional burn-in.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubtitleStyle:
    font_name: str = "PingFang TC"
    font_size: int = 30
    primary_colour: str = "&H00FFFFFF"
    outline_colour: str = "&H00181818"
    outline: float = 2.0
    shadow: float = 0.8
    margin_v: int = 48
    alignment: int = 2

    def ass_force_style(self) -> str:
        return ",".join([
            f"FontName={self.font_name}",
            f"FontSize={self.font_size}",
            f"PrimaryColour={self.primary_colour}",
            f"OutlineColour={self.outline_colour}",
            f"Outline={self.outline}",
            f"Shadow={self.shadow}",
            f"MarginV={self.margin_v}",
            f"Alignment={self.alignment}",
        ])


LANDSCAPE = SubtitleStyle(font_size=30, margin_v=48)
PORTRAIT = SubtitleStyle(font_size=42, margin_v=82, outline=2.4, shadow=1.0)


def profile_for_video(width: int | None, height: int | None) -> SubtitleStyle:
    if width and height and height > width:
        return PORTRAIT
    return LANDSCAPE
