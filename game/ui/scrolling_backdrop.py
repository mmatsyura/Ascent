import numpy as np
import pygame

from game.ui.menu_landscape import menu_landscape


class ScrollingBackdrop:
    def __init__(self, image, speed=14):
        landscape = menu_landscape(image.get_size())
        tile = pygame.surfarray.array3d(landscape).astype(np.float32)
        previous = np.roll(tile, 1, axis=1)
        self.phases = [pygame.surfarray.make_surface(np.rint(tile * (1 - phase / 4) + previous * (phase / 4)).astype(np.uint8)).convert() for phase in range(4)]
        self.height = tile.shape[1]
        self.speed = speed

    def draw(self, screen, elapsed):
        travel = (elapsed * self.speed) % self.height
        offset = int(travel)
        phase = min(3, int((travel - offset) * 4))
        image = self.phases[phase]
        for vertical in range(offset - self.height, screen.get_height(), self.height):
            screen.blit(image, (-20, vertical))
