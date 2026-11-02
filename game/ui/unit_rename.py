import math
import unicodedata

import pygame

from game.ui.clipboard import read_text, write_text
from game.ui.theme import ACCENT, BORDER, MUTED, TEXT, draw_button, panel_surface, ui_font


class UnitRename:
    def __init__(self, save_name):
        self.save_name = save_name
        self.unit = None
        self.text = ""
        self.caret = 0
        self.anchor = 0
        self.elapsed = 0
        self.scroll = 0
        self.error = ""
        self.pointer = pygame.Vector2()
        self.title_font = ui_font(21, True)
        self.font = ui_font(18)
        self.small_font = ui_font(14)
        self.panel_area = pygame.Rect(0, 0, 500, 244)
        self.input_area = pygame.Rect(0, 0, 448, 44)
        self.buttons = {}
        self.previous_repeat = (0, 0)
        self.opacity = 0
        self.buffer = None
        self.button_motion = {}
        self.frame_seconds = 1 / 60

    @property
    def active(self):
        return self.unit is not None

    @property
    def selection(self):
        return min(self.anchor, self.caret), max(self.anchor, self.caret)

    def layout(self, screen_size):
        self.panel_area.center = (screen_size[0] // 2, screen_size[1] // 2)
        self.input_area = pygame.Rect(self.panel_area.x + 26, self.panel_area.y + 89, 448, 44)
        self.buttons = {
            "cancel": pygame.Rect(self.panel_area.x + 26, self.panel_area.bottom - 62, 164, 34),
            "save": pygame.Rect(self.panel_area.right - 190, self.panel_area.bottom - 62, 164, 34),
        }
        if self.active:
            pygame.key.set_text_input_rect(self.input_area)

    def open(self, unit, screen_size):
        self.unit = unit
        self.text = unit.name
        self.anchor = 0
        self.caret = len(self.text)
        self.elapsed = 0
        self.scroll = 0
        self.error = ""
        self.previous_repeat = pygame.key.get_repeat()
        pygame.key.set_repeat(350, 35)
        self.layout(screen_size)
        pygame.key.start_text_input()

    def close(self):
        pygame.key.stop_text_input()
        pygame.key.set_repeat(*self.previous_repeat)
        self.unit = None

    def insert(self, text):
        text = unicodedata.normalize(
            "NFC", "".join(character for character in text if character.isprintable())
        )
        first, last = self.selection
        text = text[: 32 - len(self.text) + last - first]
        self.text = self.text[:first] + text + self.text[last:]
        self.caret = first + len(text)
        self.anchor = self.caret
        self.error = ""
        self.elapsed = 0

    def commit(self):
        name = " ".join(self.text.split())
        if not name:
            self.error = "Введіть назву загону."
            return
        if not self.save_name(self.unit, name):
            self.error = "Не вдалося зберегти назву. Спробуйте ще раз."
            return
        self.close()

    def handle_event(self, event):
        if event.type == pygame.TEXTINPUT:
            self.insert(event.text)
        elif event.type == pygame.KEYDOWN:
            modifiers = getattr(event, "mod", pygame.key.get_mods())
            control = bool(modifiers & pygame.KMOD_CTRL)
            shift = bool(modifiers & pygame.KMOD_SHIFT)
            if event.key == pygame.K_ESCAPE:
                self.close()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.commit()
            elif control and event.key == pygame.K_a:
                self.anchor, self.caret = 0, len(self.text)
            elif control and event.key in (pygame.K_c, pygame.K_x):
                first, last = self.selection
                write_text(self.text[first:last])
                if event.key == pygame.K_x:
                    self.insert("")
            elif control and event.key == pygame.K_v:
                pasted = " ".join(read_text().split())
                if pasted:
                    self.insert(pasted)
            elif event.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
                if self.anchor == self.caret:
                    self.anchor = (
                        max(0, self.caret - 1)
                        if event.key == pygame.K_BACKSPACE
                        else min(len(self.text), self.caret + 1)
                    )
                self.insert("")
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_HOME, pygame.K_END):
                first, last = self.selection
                if event.key == pygame.K_HOME:
                    self.caret = 0
                elif event.key == pygame.K_END:
                    self.caret = len(self.text)
                elif event.key == pygame.K_LEFT:
                    self.caret = first if first != last and not shift else max(0, self.caret - 1)
                else:
                    self.caret = (
                        last if first != last and not shift else min(len(self.text), self.caret + 1)
                    )
                if not shift:
                    self.anchor = self.caret
                self.elapsed = 0
        elif event.type == pygame.MOUSEMOTION:
            self.pointer.update(event.pos)
            if getattr(event, "buttons", (0, 0, 0))[0] and self.input_area.collidepoint(event.pos):
                self.caret = self.character_at(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.pointer.update(event.pos)
            if self.input_area.collidepoint(event.pos):
                self.caret = self.character_at(event.pos[0])
                self.anchor = self.caret
            elif self.buttons["save"].collidepoint(event.pos):
                self.commit()
            elif self.buttons["cancel"].collidepoint(event.pos):
                self.close()

    def character_at(self, horizontal):
        coordinate = horizontal - self.input_area.x - 12 + self.scroll
        return min(
            range(len(self.text) + 1),
            key=lambda index: abs(self.font.size(self.text[:index])[0] - coordinate),
        )

    def draw(self, screen, duration=1 / 60):
        self.frame_seconds = duration
        target = 1 if self.active else 0
        self.opacity += (target - self.opacity) * -math.expm1(-max(0, duration) / 0.09)
        if self.opacity < 0.005:
            return
        if self.active:
            if self.buffer is None or self.buffer.get_size() != screen.get_size():
                self.buffer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            self.buffer.fill((0, 0, 0, 0))
            self.render(self.buffer)
        if self.buffer is not None:
            self.buffer.set_alpha(round(255 * self.opacity))
            screen.blit(self.buffer, (0, 0))

    def render(self, screen):
        if not self.active:
            return
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((4, 10, 13, 155))
        screen.blit(overlay, (0, 0))
        screen.blit(panel_surface(self.panel_area.size), self.panel_area)
        screen.blit(
            self.title_font.render("Назва загону", True, ACCENT),
            (self.panel_area.x + 27, self.panel_area.y + 23),
        )
        screen.blit(
            self.small_font.render(
                "До 32 символів · Enter — зберегти · Esc — скасувати", True, MUTED
            ),
            (self.panel_area.x + 27, self.panel_area.y + 59),
        )
        pygame.draw.rect(screen, (15, 25, 29), self.input_area, border_radius=3)
        pygame.draw.rect(screen, ACCENT, self.input_area, 1, border_radius=3)
        caret_position = self.font.size(self.text[: self.caret])[0]
        self.scroll = max(0, min(self.scroll, caret_position))
        self.scroll = max(self.scroll, caret_position - self.input_area.w + 28)
        previous_clip = screen.get_clip()
        screen.set_clip(self.input_area.inflate(-16, -6))
        horizontal = self.input_area.x + 12 - self.scroll
        vertical = self.input_area.centery - self.font.get_height() // 2
        first, last = self.selection
        if first != last:
            selection_left = horizontal + self.font.size(self.text[:first])[0]
            selection_width = self.font.size(self.text[first:last])[0]
            pygame.draw.rect(
                screen,
                (46, 82, 107),
                (selection_left, vertical - 2, selection_width, self.font.get_height() + 4),
            )
        screen.blit(self.font.render(self.text, True, TEXT), (horizontal, vertical))
        if math.fmod(self.elapsed, 1) < 0.6:
            pygame.draw.line(
                screen,
                TEXT,
                (horizontal + caret_position, vertical),
                (horizontal + caret_position, vertical + self.font.get_height()),
                1,
            )
        screen.set_clip(previous_clip)
        if self.error:
            screen.blit(
                self.small_font.render(self.error, True, (230, 162, 130)),
                (self.panel_area.x + 27, self.input_area.bottom + 10),
            )
        for key, title in (("cancel", "Скасувати"), ("save", "Зберегти")):
            rectangle = self.buttons[key]
            hover = self.button_motion.get(key, 0)
            hover += (float(rectangle.collidepoint(self.pointer)) - hover) * -math.expm1(
                -max(0, self.frame_seconds) / 0.085
            )
            self.button_motion[key] = hover
            draw_button(screen, rectangle, hover)
            label = ui_font(15, True).render(title, True, TEXT)
            screen.blit(label, label.get_rect(center=rectangle.center))
