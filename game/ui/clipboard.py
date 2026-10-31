import ctypes
import os

import pygame


def read_text():
    if os.name != "nt":
        try:
            pygame.scrap.init()
            return (pygame.scrap.get(pygame.SCRAP_TEXT) or b"").decode("utf-8").rstrip("\0")
        except (pygame.error, UnicodeError):
            return ""
    user = ctypes.windll.user32
    kernel = ctypes.windll.kernel32
    user.GetClipboardData.restype = ctypes.c_void_p
    kernel.GlobalLock.argtypes = (ctypes.c_void_p,)
    kernel.GlobalLock.restype = ctypes.c_void_p
    kernel.GlobalUnlock.argtypes = (ctypes.c_void_p,)
    if not user.OpenClipboard(None):
        return ""
    try:
        handle = user.GetClipboardData(13)
        pointer = kernel.GlobalLock(handle) if handle else None
        if not pointer:
            return ""
        try:
            return ctypes.wstring_at(pointer)
        finally:
            kernel.GlobalUnlock(handle)
    finally:
        user.CloseClipboard()


def write_text(text):
    if not text:
        return
    if os.name != "nt":
        try:
            pygame.scrap.init()
            pygame.scrap.put(pygame.SCRAP_TEXT, text.encode("utf-8") + b"\0")
        except pygame.error:
            pass
        return
    user = ctypes.windll.user32
    kernel = ctypes.windll.kernel32
    kernel.GlobalAlloc.argtypes = (ctypes.c_uint, ctypes.c_size_t)
    kernel.GlobalAlloc.restype = ctypes.c_void_p
    kernel.GlobalLock.argtypes = (ctypes.c_void_p,)
    kernel.GlobalLock.restype = ctypes.c_void_p
    kernel.GlobalUnlock.argtypes = (ctypes.c_void_p,)
    kernel.GlobalFree.argtypes = (ctypes.c_void_p,)
    user.SetClipboardData.argtypes = (ctypes.c_uint, ctypes.c_void_p)
    user.SetClipboardData.restype = ctypes.c_void_p
    data = (text + "\0").encode("utf-16-le")
    if not user.OpenClipboard(None):
        return
    handle = None
    try:
        handle = kernel.GlobalAlloc(2, len(data))
        if not handle:
            return
        pointer = kernel.GlobalLock(handle)
        if not pointer:
            return
        ctypes.memmove(pointer, data, len(data))
        kernel.GlobalUnlock(handle)
        user.EmptyClipboard()
        if user.SetClipboardData(13, handle):
            handle = None
    finally:
        if handle:
            kernel.GlobalFree(handle)
        user.CloseClipboard()
