import pygame

from game.ui.theme import ACCENT, MUTED, TEXT


class InformationView:
    def __init__(self, panel):
        self.panel = panel
        self.page = 0

    def draw(self, surface, area):
        panel = self.panel
        reports = list(panel.intelligence.reports)
        if not reports:
            panel.label(surface, "Повідомлень поки немає.", (area.x + 10, area.y + 15), color=MUTED)
            panel.paragraph(
                surface,
                "Дрони передаватимуть сюди знімки міст, столиць, ворожої піхоти, техніки та споруд.",
                pygame.Rect(area.x + 10, area.y + 48, area.w - 20, 65),
            )
            return
        per_page = max(1, (area.h - 34) // 87)
        pages = (len(reports) + per_page - 1) // per_page
        self.page = max(0, min(self.page, pages - 1))
        for row, report in enumerate(reports[self.page * per_page : (self.page + 1) * per_page]):
            index = self.page * per_page + row
            rectangle = pygame.Rect(area.x, area.y + row * 87, area.w, 79)
            panel.button(surface, rectangle, "", ("report_focus", index))
            photo_width = min(106, area.w // 4)
            if report.photo is not None:
                photo = pygame.transform.smoothscale(
                    report.photo, (photo_width, round(photo_width * 90 / 160))
                )
                surface.blit(photo, (rectangle.x + 8, rectangle.centery - photo.get_height() // 2))
            else:
                surface.blit(
                    panel.icons["information"],
                    (rectangle.x + photo_width // 2 - 12, rectangle.centery - 20),
                )
            left = rectangle.x + photo_width + 19
            width = rectangle.right - left - 9
            panel.label(surface, report.title, (left, rectangle.y + 7), "button", TEXT, width=width)
            panel.label(
                surface, report.source, (left, rectangle.y + 30), "small", ACCENT, width=width
            )
            minutes, seconds = divmod(int(report.elapsed), 60)
            location = f"{minutes:02d}:{seconds:02d} · {round(report.position[0])}, {round(report.position[1])}"
            panel.label(surface, location, (left, rectangle.y + 51), "small", MUTED, width=width)
        panel.button(
            surface,
            (area.x, area.bottom - 25, 40, 25),
            "‹",
            ("information_page", -1),
            enabled=self.page > 0,
        )
        panel.label(
            surface,
            f"{self.page + 1} / {pages}",
            (area.centerx - 17, area.bottom - 23),
            "small",
            MUTED,
        )
        panel.button(
            surface,
            (area.right - 40, area.bottom - 25, 40, 25),
            "›",
            ("information_page", 1),
            enabled=self.page + 1 < pages,
        )
