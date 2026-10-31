import pygame


def prepared_sprite(image):
    image.set_alpha(image.get_alpha(), pygame.RLEACCEL)
    return image
