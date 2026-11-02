from functools import lru_cache
from pathlib import Path

import pygame

PANEL = (18, 25, 23)


TEXT = (242, 235, 211)


MUTED = (201, 204, 183)


ACCENT = (221, 190, 126)


BORDER = (128, 109, 72)


@lru_cache(maxsize=1)
def panel_texture():
    asset_path = Path(__file__).resolve().parents[1] / "assets" / "ui" / "ornate_panel.png"
    image = pygame.image.load(str(asset_path)).convert()
    return image.subsurface((6, 6, image.get_width() - 12, image.get_height() - 44)).copy()


@lru_cache(maxsize=16)
def panel_surface(size):
    source = panel_texture()
    surface = pygame.Surface(size, pygame.SRCALPHA)
    width, height = size
    body_height = height - 6
    source_corner = 270
    target_corner = min(30, body_height // 2, width // 2)
    source_columns = (0, source_corner, source.get_width() - source_corner, source.get_width())
    source_rows = (0, source_corner, source.get_height() - source_corner, source.get_height())
    target_columns = (0, target_corner, width - target_corner, width)
    target_rows = (0, target_corner, body_height - target_corner, body_height)

    for offset, opacity in [(0, 15), (2, 25), (4, 40)]:
        pygame.draw.rect(
            surface,
            (0, 0, 0, opacity),
            (offset, 6, width - offset * 2, height - 6 - offset),
            border_radius=5,
        )

    for row in range(3):
        for column in range(3):
            source_area = pygame.Rect(
                source_columns[column],
                source_rows[row],
                source_columns[column + 1] - source_columns[column],
                source_rows[row + 1] - source_rows[row],
            )
            target_area = pygame.Rect(
                target_columns[column],
                target_rows[row],
                target_columns[column + 1] - target_columns[column],
                target_rows[row + 1] - target_rows[row],
            )
            if target_area.width and target_area.height:
                section = pygame.transform.smoothscale(
                    source.subsurface(source_area), target_area.size
                )
                surface.blit(section, target_area)

    interior = pygame.Rect(17, 16, width - 34, body_height - 32)
    if interior.w > 0 and interior.h > 0:
        for row in range(interior.h):
            progress = row / max(1, interior.h - 1)
            color = tuple(
                round(first + (last - first) * progress)
                for first, last in zip((27, 36, 32), (14, 22, 21))
            )
            pygame.draw.line(
                surface,
                color,
                (interior.left, interior.top + row),
                (interior.right - 1, interior.top + row),
            )
        pygame.draw.line(
            surface, (84, 80, 58), interior.topleft, (interior.right - 1, interior.top)
        )
        pygame.draw.line(
            surface,
            (7, 14, 14),
            (interior.left, interior.bottom - 1),
            (interior.right - 1, interior.bottom - 1),
        )
    return surface


def draw_button(surface, rectangle, hovered=False, pressed=False):
    rectangle = pygame.Rect(rectangle)
    image = button_surface(
        rectangle.size,
        round(max(0, min(1, float(hovered))) * 16),
        round(max(0, min(1, float(pressed))) * 16),
    )
    surface.blit(image, rectangle)


@lru_cache(maxsize=192)
def button_surface(size, hover_step, press_step):
    surface = pygame.Surface(size, pygame.SRCALPHA)
    rectangle = surface.get_rect()
    hover = hover_step / 16
    press = press_step / 16
    background = tuple(
        round(start + (end - start) * hover) for start, end in zip((28, 39, 34), (49, 62, 51))
    )
    background = tuple(
        round(start + (end - start) * press) for start, end in zip(background, (18, 28, 25))
    )
    border = tuple(round(start + (end - start) * hover) for start, end in zip(BORDER, ACCENT))
    pygame.draw.rect(surface, (8, 15, 13), rectangle.move(0, 2), border_radius=3)
    pygame.draw.rect(surface, background, rectangle, border_radius=3)
    for row in range(2, max(2, rectangle.h - 2)):
        light = 7 * (1 - row / max(1, rectangle.h - 1)) - 4
        color = tuple(max(0, min(255, round(channel + light))) for channel in background)
        pygame.draw.line(surface, color, (2, row), (rectangle.w - 3, row))
    pygame.draw.rect(surface, border, rectangle, 1, border_radius=3)
    pygame.draw.line(
        surface,
        (102, 111, 81),
        (rectangle.left + 3, rectangle.top + 2),
        (rectangle.right - 4, rectangle.top + 2),
    )
    if rectangle.w >= 80:
        length = min(18, rectangle.w // 5)
        pygame.draw.line(surface, border, (4, rectangle.h - 3), (4 + length, rectangle.h - 3))
        pygame.draw.line(surface, border, (rectangle.w - 5 - length, 3), (rectangle.w - 5, 3))
    return surface


@lru_cache(maxsize=32)
def ui_font(size=15, bold=False):
    path = pygame.font.match_font("tahoma", bold=bold)
    if path is None:
        path = pygame.font.match_font("dejavusans,arial", bold=bold)
    return pygame.font.Font(path, max(13, round(size)))


def fit_text(font, text, width):
    if font.size(text)[0] <= width:
        return text
    while text and font.size(text + "…")[0] > width:
        text = text[:-1]
    return text.rstrip() + "…"


class SmoothLayer:
    def __init__(self, duration=0.18):
        self.duration = duration
        self.source = None
        self.previous = None
        self.image = None
        self.position = pygame.Vector2()
        self.target_position = pygame.Vector2()
        self.progress = 1

    def set(self, image, position):
        self.target_position.update(position)
        if image is self.source:
            return
        self.previous = self.image.copy() if self.image is not None else None
        self.source = image
        self.progress = 0
        if self.previous is None:
            self.position.update(position)

    def draw(self, screen, duration):
        self.progress = min(1, self.progress + max(0, duration) / self.duration)
        blend = self.progress * self.progress * (3 - 2 * self.progress)
        self.position += (self.target_position - self.position) * min(1, max(0, duration) * 22)
        if self.progress >= 1:
            self.image = self.source
            self.previous = None
        else:
            sizes = [
                image.get_size() for image in (self.previous, self.source) if image is not None
            ]
            if not sizes:
                self.image = None
                return
            size = (max(width for width, _ in sizes), max(height for _, height in sizes))
            image = pygame.Surface(size, pygame.SRCALPHA)
            if self.previous is not None:
                previous = self.previous.copy()
                if self.source is None or self.source.get_size() != self.previous.get_size():
                    previous.set_alpha(round(255 * (1 - blend)))
                image.blit(previous, (0, 0))
            if self.source is not None:
                current = self.source.copy()
                current.set_alpha(round(255 * blend))
                image.blit(current, (0, 0))
            self.image = image
        if self.image is not None:
            screen.blit(self.image, (round(self.position.x), round(self.position.y)))

    def contains(self, position):
        return self.image is not None and self.image.get_rect(topleft=self.position).collidepoint(
            position
        )
