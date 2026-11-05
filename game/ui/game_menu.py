import pygame

from game.ui.menu_settings import MenuSettings
from game.ui.menu_view import MenuView


class GameMenu:
    def __init__(self, app):
        self.app = app
        self.state = "main"
        self.parent = "main"
        self.started = False
        self.elapsed = 0
        self.open_age = 0
        self.buttons = {}
        self.sliders = {}
        self.keyboard_index = -1
        self.pressed = None
        self.drag_slider = None
        self.snapshot = None
        self.fade_frame = None
        self.close_age = 0
        self.settings = MenuSettings(app)
        self.view = MenuView(self)
        self.app.command_panel.paused = True

    @property
    def active(self):
        return self.state is not None

    def show(self, state):
        self.state = state
        self.open_age = 0
        self.buttons = {}
        self.sliders = {}
        self.keyboard_index = -1
        self.pressed = None
        self.drag_slider = None

    def begin(self):
        if self.app.defeat.achieved:
            return
        self.fade_frame = self.app.screen.copy()
        self.app.fps_counter.erase(self.fade_frame)
        self.close_age = 0
        self.started = True
        self.state = None
        self.buttons = {}
        self.app.command_panel.paused = False
        self.app.clock.tick()

    def pause(self):
        if self.active:
            return
        self.snapshot = self.app.screen.copy()
        self.app.fps_counter.erase(self.snapshot)
        self.view.pause_background = None
        self.app.cancel_drag()
        self.app.building_operations.selected = None
        self.app.command_panel.paused = True
        self.show("pause")
        if pygame.mixer.get_init() is not None:
            for channel in (
                self.app.soundscape.purchase_channel,
                self.app.soundscape.explosion_channel,
                self.app.soundscape.notification_channel,
            ):
                if channel is not None:
                    channel.fadeout(140)

    def activate(self, action):
        self.app.soundscape.click()
        if action == "resume":
            self.begin()
        elif action == "new":
            if self.app.defeat.achieved:
                self.app.restart_requested = True
            elif self.started:
                self.parent = self.state
                self.show("confirm_new")
            else:
                self.begin()
        elif action in ("settings", "controls"):
            self.parent = self.state
            self.show(action)
        elif action == "home":
            self.show("main")
        elif action == "back":
            self.back()
        elif action == "quit":
            self.parent = self.state
            self.show("confirm_exit")
        elif action == "confirm_exit":
            self.app.running = False
        elif action == "confirm_new":
            self.app.restart_requested = True
        elif action == "window":
            self.app.handle_key(pygame.K_F11)
        elif action == "fps":
            self.settings.show_fps = not self.settings.show_fps
            self.settings.save()

    def back(self):
        if self.state == "pause":
            self.begin()
        elif self.state == "main":
            if self.started:
                self.begin()
        else:
            self.settings.save()
            self.show(self.parent)

    def handle(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                self.app.handle_key(event.key)
            elif event.key == pygame.K_ESCAPE:
                self.back()
            elif event.key == pygame.K_SPACE and self.state == "pause":
                self.begin()
            elif event.key in (pygame.K_DOWN, pygame.K_UP, pygame.K_TAB):
                if self.buttons:
                    self.keyboard_index = (
                        self.keyboard_index + (-1 if event.key == pygame.K_UP else 1)
                    ) % len(self.buttons)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                actions = list(self.buttons)
                if actions:
                    self.activate(actions[max(0, self.keyboard_index)])
        elif event.type == pygame.MOUSEMOTION:
            self.keyboard_index = -1
            if self.drag_slider:
                self.slide(self.drag_slider, event.pos[0])
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, area in self.sliders.items():
                if area.inflate(16, 24).collidepoint(event.pos):
                    self.drag_slider = key
                    self.slide(key, event.pos[0])
                    return
            self.pressed = next(
                (key for key, area in self.buttons.items() if area.collidepoint(event.pos)), None
            )
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.drag_slider:
                self.slide(self.drag_slider, event.pos[0])
                self.drag_slider = None
                self.settings.save()
            action = self.pressed
            self.pressed = None
            if action in self.buttons and self.buttons[action].collidepoint(event.pos):
                self.activate(action)

    def slide(self, key, x):
        area = self.sliders[key]
        self.settings.set(key, (x - area.left) / area.w)

    def update(self, duration):
        self.elapsed += duration
        if self.active:
            self.open_age += duration
        elif self.fade_frame is not None:
            self.close_age += duration
            if self.close_age >= 0.24:
                self.fade_frame = None

    def draw_exit(self, screen):
        if self.fade_frame is None:
            return
        progress = min(1, self.close_age / 0.24)
        self.fade_frame.set_alpha(round(255 * (1 - progress * progress * (3 - 2 * progress))))
        screen.blit(self.fade_frame, (0, 0))

    def draw(self, screen):
        self.view.draw(screen)
