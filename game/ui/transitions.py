import pygame


class SmoothLayer:
    def __init__(self, duration=.18):
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
            sizes = [image.get_size() for image in (self.previous, self.source) if image is not None]
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
        return self.image is not None and self.image.get_rect(topleft=self.position).collidepoint(position)
