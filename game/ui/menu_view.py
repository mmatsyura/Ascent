from functools import lru_cache
import math

import pygame

from game.ui.menu_background import ScrollingBackdrop
from game.ui.theme import ACCENT, MUTED, TEXT, panel_surface, ui_font


@lru_cache(maxsize=160)
def text_image(text, size, color=TEXT, bold=False):
    return ui_font(size, bold).render(text, True, color)


def loading_screen(screen):
    screen.fill((12, 21, 23))
    title = text_image("ASCENT", 72, ACCENT, True)
    screen.blit(
        title, title.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 - 28))
    )
    label = text_image("Підготовка кампанії…", 16, MUTED)
    screen.blit(
        label, label.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 + 42))
    )
    pygame.display.flip()
    pygame.event.pump()


class MenuView:
    def __init__(self, menu):
        self.menu = menu
        self.map_image = menu.app.terrain.create_overview((1280, 880))
        self.background = None
        self.size = None
        self.pause_background = None
        self.pause_size = None
        self.hover = {}
        self.content = None

    def label(self, surface, text, point, size=16, color=TEXT, bold=False):
        surface.blit(text_image(text, size, color, bold), point)

    def background_image(self, size):
        if self.size == size:
            return
        self.size = size
        width, height = size
        image = pygame.Surface((width + 40, height + 40))
        ratio = max(
            image.get_width() / self.map_image.get_width(),
            image.get_height() / self.map_image.get_height(),
        )
        scaled = pygame.transform.smoothscale(
            self.map_image,
            (round(self.map_image.get_width() * ratio), round(self.map_image.get_height() * ratio)),
        )
        image.blit(scaled, scaled.get_rect(center=image.get_rect().center))
        image.fill((95, 121, 112), special_flags=pygame.BLEND_RGB_MULT)
        self.scrolling_map = ScrollingBackdrop(image)
        shade = pygame.Surface((width + 40, height + 40), pygame.SRCALPHA)
        for x in range(width + 40):
            distance = x / (width + 40)
            alpha = round(238 - 100 * distance + 25 * distance**3)
            pygame.draw.line(shade, (9, 18, 23, alpha), (x, 0), (x, height + 40))
        image.blit(shade, (0, 0))
        grid = pygame.Surface(image.get_size(), pygame.SRCALPHA)
        for x in range(0, width + 40, 80):
            pygame.draw.line(grid, (178, 185, 151, 11), (x, 0), (x, height + 40))
        for y in range(0, height + 40, 80):
            pygame.draw.line(grid, (178, 185, 151, 11), (0, y), (width + 40, y))
        center = pygame.Vector2(width * 0.76, height * 0.47)
        for radius in (110, 210, 310):
            pygame.draw.circle(grid, (192, 171, 117, 25), center, radius, 1)
        points = [
            (width * 0.6, height * 0.23),
            (width * 0.77, height * 0.35),
            (width * 0.68, height * 0.53),
            (width * 0.85, height * 0.72),
        ]
        pygame.draw.lines(grid, (197, 177, 127, 45), False, points, 1)
        for point in points:
            pygame.draw.circle(grid, (221, 190, 126, 95), point, 4, 1)
            pygame.draw.line(
                grid, (221, 190, 126, 65), (point[0] - 9, point[1]), (point[0] + 9, point[1]), 1
            )
            pygame.draw.line(
                grid, (221, 190, 126, 65), (point[0], point[1] - 9), (point[0], point[1] + 9), 1
            )
        image.blit(grid, (0, 0))
        self.fixed_overlay = shade.copy()
        self.fixed_overlay.blit(grid, (0, 0))
        self.background = image

    def button(self, surface, action, label, rectangle, primary=False, hint=None):
        menu = self.menu
        rectangle = pygame.Rect(rectangle)
        menu.buttons[action] = rectangle
        pointer = pygame.mouse.get_pos()
        index = list(menu.buttons).index(action)
        target = rectangle.collidepoint(pointer) or menu.keyboard_index == index
        value = self.hover.get(action, 0)
        value += (float(target) - value) * -math.expm1(-max(0, menu.app.interface_seconds) / 0.085)
        self.hover[action] = value
        pressed = menu.pressed == action and target
        if primary:
            low = (178, 146, 86)
            high = (228, 198, 132)
            color = tuple(round(a + (b - a) * value) for a, b in zip(low, high))
            if pressed:
                color = tuple(round(channel * 0.85) for channel in color)
            pygame.draw.rect(surface, color, rectangle, border_radius=3)
            pygame.draw.rect(surface, (238, 214, 159), rectangle, 1, border_radius=3)
            ink = (22, 30, 28)
        else:
            color = tuple(round(a + (b - a) * value) for a, b in zip((19, 31, 32), (42, 54, 48)))
            pygame.draw.rect(surface, color, rectangle, border_radius=3)
            pygame.draw.rect(
                surface,
                tuple(round(a + (b - a) * value) for a, b in zip((82, 91, 78), (190, 169, 111))),
                rectangle,
                1,
                border_radius=3,
            )
            ink = TEXT
        pygame.draw.line(
            surface,
            (239, 212, 154) if primary else (107, 116, 92),
            (rectangle.x + 2, rectangle.y + 2),
            (rectangle.right - 3, rectangle.y + 2),
        )
        if value > 0.01:
            pygame.draw.rect(
                surface,
                ACCENT,
                (rectangle.x, rectangle.y + 12, max(2, round(3 * value)), rectangle.h - 24),
            )
        title = text_image(label, 17, ink, True)
        surface.blit(title, title.get_rect(midleft=(rectangle.x + 22, rectangle.centery)))
        if hint:
            note = text_image(hint, 13, (65, 66, 48) if primary else MUTED)
            surface.blit(note, note.get_rect(midright=(rectangle.right - 18, rectangle.centery)))
        else:
            self.label(surface, "›", (rectangle.right - 27, rectangle.centery - 15), 25, ink)

    def draw(self, screen):
        menu = self.menu
        width, height = screen.get_size()
        self.background_image(screen.get_size())
        if (
            menu.state == "main"
            or menu.parent == "main"
            and menu.state in ("settings", "controls", "confirm_exit", "confirm_new")
        ):
            self.scrolling_map.draw(screen, menu.elapsed)
            screen.blit(self.fixed_overlay, (-20, -20))
        else:
            if self.pause_background is None or self.pause_size != screen.get_size():
                source = menu.snapshot if menu.snapshot is not None else self.background
                small = pygame.transform.smoothscale(
                    source, (max(1, width // 14), max(1, height // 14))
                )
                self.pause_background = pygame.transform.smoothscale(small, (width, height))
                self.pause_background.fill((88, 102, 101), special_flags=pygame.BLEND_RGB_MULT)
                self.pause_size = screen.get_size()
            screen.blit(self.pause_background, (0, 0))
            if menu.state == "pause" and menu.snapshot is not None and menu.open_age < 0.24:
                snapshot = menu.snapshot
                if snapshot.get_size() != screen.get_size():
                    snapshot = pygame.transform.smoothscale(snapshot, screen.get_size())
                snapshot.set_alpha(round(255 * (1 - min(1, menu.open_age / 0.24))))
                screen.blit(snapshot, (0, 0))
        if self.content is None or self.content.get_size() != screen.get_size():
            self.content = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        content = self.content
        content.fill((0, 0, 0, 0))
        menu.buttons = {}
        menu.sliders = {}
        if menu.state == "main":
            self.main(content)
        else:
            self.card(content)
        progress = min(1, menu.open_age / 0.24)
        opacity = progress * progress * (3 - 2 * progress)
        content.set_alpha(round(255 * opacity))
        screen.blit(content, (0, 0))

    def main(self, surface):
        menu = self.menu
        width, height = surface.get_size()
        x = max(44, round(width * 0.08))
        y = max(45, round(height * 0.12))
        title_size = max(74, min(120, round(height * 0.135)))
        self.label(surface, "СТРАТЕГІЯ У РЕАЛЬНОМУ ЧАСІ", (x + 3, y), 13, ACCENT, True)
        title = text_image("ASCENT", title_size, TEXT, True)
        surface.blit(title, (x - 4, y + 29))
        line_y = y + title_size + 49
        pygame.draw.line(surface, ACCENT, (x, line_y), (x + 60, line_y), 2)
        pygame.draw.line(surface, (90, 99, 83), (x + 76, line_y), (x + 318, line_y), 1)
        self.label(surface, "Кожен наказ змінює кордони.", (x, line_y + 18), 17, MUTED)
        button_y = line_y + 69
        button_width = min(370, width - 2 * x)
        button_height = 42 if height < 720 else 52
        actions = (
            [("resume", "Продовжити", True)] if menu.started else [("new", "Нова кампанія", True)]
        )
        if menu.started:
            actions.append(("new", "Нова кампанія", False))
        actions.extend(
            (
                ("settings", "Налаштування", False),
                ("controls", "Керування", False),
                ("quit", "Вийти з гри", False),
            )
        )
        for index, (action, label, primary) in enumerate(actions):
            self.button(
                surface,
                action,
                label,
                (
                    x,
                    button_y + index * (button_height + (8 if height < 720 else 10)),
                    button_width,
                    button_height,
                ),
                primary,
            )
        if width >= 1100:
            card = pygame.Rect(width - 380, round(height * 0.61), 300, 149)
            pygame.draw.line(surface, (139, 133, 93), card.topleft, card.topright, 1)
            self.label(surface, "КАМПАНІЯ  I", (card.x, card.y + 18), 13, ACCENT, True)
            self.label(surface, "Чотири держави", (card.x, card.y + 43), 24, TEXT, True)
            self.label(surface, "Розвідка. Контроль. Перевага.", (card.x, card.y + 83), 15, MUTED)
            self.label(surface, "Здобудьте 80% території.", (card.x, card.y + 108), 14, MUTED)
        pygame.draw.line(surface, (67, 79, 72), (x, height - 54), (width - x, height - 54))
        self.label(surface, "СИНЄ КОРОЛІВСТВО", (x, height - 37), 12, ACCENT, True)
        note = (
            "Поточна партія — до закриття гри"
            if menu.started
            else "Ваша історія починається з першого наказу"
        )
        text = text_image(note, 12, MUTED)
        if width >= 1000:
            surface.blit(text, text.get_rect(topright=(width - x, height - 37)))

    def card(self, surface):
        menu = self.menu
        width, height = surface.get_size()
        card_height = (
            536
            if menu.state == "pause"
            else 484 if menu.state == "controls" else 492 if menu.state == "settings" else 340
        )
        card_height = min(card_height, height - 40)
        area = pygame.Rect(0, 0, min(490, width - 40), card_height)
        area.center = (width // 2, height // 2)
        surface.blit(panel_surface(area.size), area)
        x = area.x + 34
        right = area.right - 34
        header = {
            "pause": ("ПАУЗА", "Час зупинено"),
            "settings": ("НАЛАШТУВАННЯ", "Звук і зображення"),
            "controls": ("КЕРУВАННЯ", "Ваші накази"),
            "confirm_exit": ("ВИХІД ІЗ ГРИ", "Вийти з гри?"),
            "confirm_new": ("НОВА КАМПАНІЯ", "Почати спочатку?"),
        }[menu.state]
        self.label(surface, header[0], (x, area.y + 31), 12, ACCENT, True)
        self.label(surface, header[1], (x, area.y + 56), 29, TEXT, True)
        pygame.draw.line(surface, (113, 104, 75), (x, area.y + 107), (right, area.y + 107))
        y = area.y + 127
        button_width = right - x
        if menu.state == "pause":
            self.label(surface, "Кампанія чекає на ваш наступний крок.", (x, y), 14, MUTED)
            actions = (
                ("resume", "Продовжити гру", True, "ESC"),
                ("settings", "Налаштування", False, None),
                ("controls", "Керування", False, None),
                ("home", "До головного меню", False, None),
                ("quit", "Вийти з гри", False, None),
            )
            for index, (action, label, primary, hint) in enumerate(actions):
                self.button(
                    surface,
                    action,
                    label,
                    (x, y + 39 + index * 57, button_width, 46),
                    primary,
                    hint,
                )
            self.label(
                surface, "Симуляцію та всі таймери призупинено.", (x, area.bottom - 42), 13, MUTED
            )
        elif menu.state == "settings":
            for index, (key, label) in enumerate(
                (("music", "Музика"), ("effects", "Звукові ефекти"))
            ):
                row_y = y + index * 83
                self.label(surface, label, (x, row_y), 16, TEXT, True)
                value = getattr(menu.settings, key)
                value_text = text_image(f"{round(value*100)}%", 14, ACCENT, True)
                surface.blit(value_text, value_text.get_rect(topright=(right, row_y)))
                track = pygame.Rect(x, row_y + 37, button_width, 5)
                menu.sliders[key] = track
                pygame.draw.rect(surface, (45, 58, 52), track, border_radius=2)
                pygame.draw.rect(
                    surface,
                    (195, 167, 108),
                    (track.x, track.y, round(track.w * value), track.h),
                    border_radius=2,
                )
                center = (round(track.x + track.w * value), track.centery)
                pygame.draw.circle(surface, (20, 29, 27), center, 10)
                pygame.draw.circle(surface, ACCENT, center, 7)
                pygame.draw.circle(surface, (247, 223, 170), center, 3)
            mode = "На весь екран" if menu.app.fullscreen else "У вікні"
            self.button(surface, "window", mode, (x, y + 170, button_width, 41), hint="F11")
            self.button(
                surface,
                "fps",
                "Лічильник FPS",
                (x, y + 222, button_width, 41),
                hint="Увімкнено" if menu.settings.show_fps else "Вимкнено",
            )
            self.button(
                surface, "back", "Назад", (x, area.bottom - 78, button_width, 44), hint="ESC"
            )
            if menu.settings.message:
                self.label(surface, menu.settings.message, (x, area.bottom - 27), 12, MUTED)
        elif menu.state == "controls":
            rows = (
                ("WASD / стрілки", "Переміщення карти"),
                ("Колесо миші", "Масштаб карти"),
                ("ЛКМ / ПКМ", "Вибір / наказ підрозділу"),
                ("Ctrl + ЛКМ", "Рамка вибору"),
                ("F2", "Перейменувати підрозділ"),
                ("Home", "Огляд усієї карти"),
                ("Esc / Пробіл", "Меню паузи"),
            )
            for index, (key, label) in enumerate(rows):
                row_y = y + index * 32
                self.label(surface, key, (x, row_y), 14, ACCENT, True)
                self.label(surface, label, (x + 153, row_y), 14, MUTED)
            self.button(
                surface, "back", "Назад", (x, area.bottom - 76, button_width, 44), hint="ESC"
            )
        else:
            lines = (
                ("Поточний прогрес буде втрачено.", "Нова кампанія почнеться з початкових умов.")
                if menu.state == "confirm_new"
                else (
                    "Поточна партія не зберігається після виходу.",
                    "Залишитися та продовжити гру?",
                )
            )
            for index, line in enumerate(lines):
                self.label(surface, line, (x, y + index * 28), 14, MUTED)
            self.button(
                surface, "back", "Залишитися", (x, area.bottom - 111, button_width, 42), True
            )
            self.button(
                surface,
                menu.state,
                "Почати нову гру" if menu.state == "confirm_new" else "Вийти",
                (x, area.bottom - 61, button_width, 39),
            )
