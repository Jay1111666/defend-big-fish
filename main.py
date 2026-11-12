"""保卫大肥鱼 · 云端花园。支持源码与独立 exe 启动。"""
import argparse
import asyncio
import math
import os
import sys
from pathlib import Path

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
from config import (WIDTH, HEIGHT, COLS, PADS, TOWERS,
                    LEVEL_NAMES, CHARACTERS, FIRST_CLEAR_STARS, pad_at, portrait_key)
from model import Game, Enemy
from progress import ProgressStore, open_progress, SAVE_ERRORS
from game_audio import GameAudio
from art import Art, ROOT, text, panel, star, draw_enemy, draw_effect, draw_laser, WHITE, MUTED, PLUM, TEAL


class App:
    def __init__(self, progress=None, browser=False):
        self.browser = browser
        self.started = not browser
        pygame.init()
        pygame.display.set_caption('保卫大肥鱼 · 云端花园')
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.art = Art()
        icon = pygame.Surface((64, 64), pygame.SRCALPHA)
        self.art.sprite(icon, 'whale', (32, 32), (64, 64))
        pygame.display.set_icon(icon)
        self.clock = pygame.time.Clock()
        self.progress = open_progress() if progress is None else progress
        self.profile = self.progress.snapshot()
        self.audio = GameAudio(ROOT / 'assets' / 'audio', self.progress.audio_settings(), deferred=browser)
        self.game = Game()
        self.settings_open = False
        self.settings_notice = ''
        self.selected = None
        self.build_pad = None
        self.paused = False
        self.speed = 1
        self.menu = False
        self.shop = False
        self.shop_notice = '兑换后点击使用角色，就能与她一起冒险。'
        self.reward_settled = False
        self.reward_message = ''
        self.buttons = []
        self.popup = None
        self.notice = '点击任意空地，选择防御塔。准备好后开始第一波！'
        self.tick = 0
        self.pointer = (0, 0)

    def mouse_position(self):
        return self.pointer if self.browser else pygame.mouse.get_pos()

    def reset(self, level):
        self.game = Game(level)
        self.art.set_map(self.game.layout)
        self.audio.clear_hits()
        self.settings_open = False
        self.selected = self.build_pad = None
        self.paused = self.menu = False
        self.shop = False
        self.reward_settled = False
        self.reward_message = ''
        self.speed = 1
        self.notice = '点击任意空地，选择防御塔。准备好后开始第一波！'

    def button(self, rect, label, action, enabled=True, color=TEAL, size=17):
        rect = pygame.Rect(rect)
        hover = rect.collidepoint(self.mouse_position())
        panel(self.screen, rect.move(0, 4), (45, 36, 69), radius=15)
        panel(self.screen, rect, color if enabled else (134, 124, 153), WHITE if hover and enabled else None, 15)
        text(self.screen, label, rect.center, size, WHITE, True, True)
        self.buttons.append((rect, action, enabled))

    def draw_hud(self):
        s, g = self.screen, self.game
        panel(s, (20, 18, WIDTH - 40, 80), (58, 45, 87), (131, 110, 159), 25)
        pygame.draw.circle(s, (185, 127, 68), (64, 58), 25)
        pygame.draw.circle(s, (255, 214, 113), (64, 54), 24)
        pygame.draw.circle(s, (255, 238, 166), (64, 54), 19, 2)
        star(s, (64, 54), 13, (202, 148, 58))
        text(s, g.coins, (103, 30), 29, WHITE, bold=True)
        text(s, '金币', (104, 70), 11, (219, 195, 235))
        self.art.sprite(s, 'currency', (207, 54), (39, 39))
        text(s, self.profile.stars, (234, 33), 27, (227, 224, 255), bold=True)
        text(s, '星声', (236, 70), 11, (219, 195, 235))
        text(s, f'{g.level + 1:02d}  {g.config["name"]}', (345, 32), 18, WHITE, bold=True)
        text(s, f'第 {max(0, g.waves.index + 1)} / {len(g.config["waves"])} 波', (346, 63), 14, (221, 204, 240))
        status = '暂停中 · 可布置' if self.paused else ('怪兽来袭' if g.waves.active else '准备布置')
        panel(s, (510, 33, 150, 46), (44, 34, 68), radius=20)
        text(s, status, (585, 55), 16, (255, 229, 164), True, True)
        text(s, f'生命 {g.lives}', (681, 43), 20, (255, 180, 198), bold=True)
        self.button((765, 34, 81, 42), f'{self.speed}× 倍速', 'speed', size=15)
        self.button((854, 34, 70, 42), '继续' if self.paused else '暂停', 'pause', color=(107, 88, 162), size=16)
        self.button((932, 34, 70, 42), '商店', 'shop', color=(194, 132, 69), size=16)
        self.button((1010, 34, 70, 42), '选关', 'menu', color=(107, 88, 162), size=16)
        self.button((1088, 34, 70, 42), '重开', 'restart', color=(107, 88, 162), size=16)
        self.button((1166, 34, 72, 42), '设置', 'settings', color=(107, 88, 162), size=16)
        panel(s, (20, 726, WIDTH - 40, 59), (250, 241, 252), (224, 206, 239), 20)
        text(s, '保卫大肥鱼', (39, 737), 23, PLUM, bold=True)
        text(s, g.config['name'] if g.level else '云端花园', (41, 766), 11, MUTED)
        old_clip = s.get_clip()
        s.set_clip((205, 730, 800, 50))
        text(s, self.notice, (205, 746), 16, PLUM)
        s.set_clip(old_clip)
        label = '正在守护…' if g.waves.active else ('开始第一波 [空格]' if g.waves.index < 0 else '开始下一波 [空格]')
        self.button((1022, 736, 220, 39), label, 'wave', not g.waves.active and g.state == 'playing', size=17)
        if self.selected is not None or self.build_pad is not None or g.priority_target is not None:
            self.button((1110, 675, 130, 34), '取消选择', 'cancel', color=(107, 88, 162), size=15)

    def draw_selection(self):
        s = self.screen
        if self.build_pad is None and self.selected is None:
            return
        pad = self.selected.pad if self.selected else self.build_pad
        x, y = PADS[pad]
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        if self.build_pad is not None:
            for i, (gx, gy) in enumerate(PADS):
                if abs(gx - x) <= 128 and abs(gy - y) <= 128 and self.game.can_build(i):
                    pygame.draw.rect(overlay, (255, 247, 255, 75), (gx - 30, gy - 30, 60, 60), 1, 10)
        radius = self.selected.radius if self.selected else None
        if self.build_pad is not None:
            for rect, action, _ in self.buttons:
                if action in TOWERS and rect.collidepoint(self.mouse_position()):
                    radius = TOWERS[action]['radius']
        if radius:
            pygame.draw.circle(overlay, (224, 255, 213, 32), (x, y), radius)
            pygame.draw.circle(overlay, (241, 255, 216, 150), (x, y), radius, 2)
        if self.selected and self.selected.aura_radius:
            pygame.draw.circle(overlay, (255, 204, 82, 190), (x, y), self.selected.aura_radius, 3)
            for other in self.game.towers:
                if self.selected.supports(other):
                    pygame.draw.circle(overlay, (255, 213, 92, 210), other.position, 32, 2)
        pygame.draw.rect(overlay, (255, 255, 255, 245), (x - 30, y - 30, 60, 60), 3, 12)
        s.blit(overlay, (0, 0))
        if self.build_pad is not None:
            text(s, '+', (x, y - 3), 39, WHITE, True, True)

    def draw_popup(self):
        if self.build_pad is None and self.selected is None:
            self.popup = None
            return
        s, g = self.screen, self.game
        pad = self.selected.pad if self.selected else self.build_pad
        x, y = PADS[pad]
        width = 6 + 98 * len(TOWERS) if self.build_pad is not None else 300
        height = 155 if self.build_pad is not None else 142
        left = max(26, min(WIDTH - width - 26, x - width / 2))
        top = y + 45
        if top + height > 715:
            top = y - height - 45
        self.popup = pygame.Rect(left, top, width, height)
        panel(s, self.popup.move(0, 6), (112, 83, 142), radius=20)
        panel(s, self.popup, (255, 246, 253), (230, 210, 243), 20)
        if self.build_pad is not None:
            text(s, '在此建造', (left + 18, top + 9), 15, PLUM, bold=True)
            text(s, '点击取消选择' if self.browser else '右键取消', (left + width - 95, top + 10), 12, MUTED)
            for i, (kind, spec) in enumerate(TOWERS.items()):
                cx = left + 52 + i * 98
                enabled = g.coins >= spec['cost']
                rect = pygame.Rect(cx - 43, top + 34, 86, 111)
                hover = rect.collidepoint(self.mouse_position())
                panel(s, rect, (232, 245, 224) if hover and enabled else (238, 228, 245), TEAL if hover and enabled else None, 13)
                self.art.turret(s, kind, (cx, top + 69), preview=True)
                text(s, spec['name'], (cx, top + 110), 14, PLUM, True, True)
                text(s, f'● {spec["cost"]}', (cx, top + 132), 16, (155, 111, 44) if enabled else (174, 157, 175), True, True)
                self.buttons.append((rect, kind, enabled))
        else:
            t = self.selected
            text(s, f'{TOWERS[t.kind]["name"]}  Lv.{t.level}', (left + 16, top + 10), 20, PLUM, bold=True)
            text(s, f'射程 {t.radius}  ·  最高三级', (left + 16, top + 41), 13, MUTED)
            if t.kind == 'bottle':
                detail = '满级光环：周围 160 像素攻速 +25%'
            elif g.attack_speed_for(t) > 1:
                detail = '光环加成：激光伤害 +25%' if t.kind == 'magic' else '光环加成：攻击速度 +25%'
            else:
                detail = TOWERS[t.kind]['subtitle']
            text(s, detail, (left + 16, top + 65), 13, (146, 102, 35))
            self.button((left + 12, top + 94, 134, 35), f'升级 {t.upgrade_cost}' if t.level < 3 else '已满级', 'upgrade', t.level < 3 and g.coins >= t.upgrade_cost, size=15)
            self.button((left + 155, top + 94, 132, 35), f'出售 +{int(t.spent * .7)}', 'sell', color=(144, 114, 164), size=15)

    def draw_modal(self):
        g, s = self.game, self.screen
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((36, 24, 59, 170))
        s.blit(shade, (0, 0))
        self.buttons = []
        if self.menu:
            panel(s, (300, 170, 680, 465))
            text(s, '云端冒险 · 十段旅程', (640, 216), 29, PLUM, True, True)
            text(s, '跨越雪原、冰港与溪谷 · 第十关迎战手柄大魔王', (640, 263), 17, MUTED, True)
            for i, name in enumerate(LEVEL_NAMES):
                cleared = '  已首通' if i in self.profile.cleared else f'  +{FIRST_CLEAR_STARS}星声'
                self.button((330 + i % 2 * 320, 300 + i // 2 * 49, 300, 40), f'{i + 1:02d}  {name}{cleared}', f'level:{i}', color=(122, 99, 165), size=15)
            self.button((530, 567, 220, 42), '返回当前对局', 'menu')
        else:
            panel(s, (400, 235, 480, 315))
            text(s, '守护成功！' if g.state == 'won' else '伙伴需要更强的防线', (640, 292), 28, PLUM, True, True)
            text(s, f'击退 {g.kills} 个敌人 · 剩余生命 {g.lives}', (640, 352), 19, MUTED, True)
            text(s, self.reward_message if g.state == 'won' else '试试在转角搭配月亮与弓箭塔', (640, 390), 16, MUTED, True)
            if g.state == 'won' and not self.reward_settled:
                self.button((550, 404, 180, 33), '重试领取星声', 'reward', size=14)
                return
            self.button((425, 451, 195, 48), '再来一次', 'restart')
            next_level = g.level < 9 and g.state == 'won'
            self.button((640, 451, 215, 48), '下一关' if next_level else '选择关卡', 'next' if next_level else 'menu', color=(122, 99, 165))
            self.button((550, 510, 180, 30), '星声商店', 'shop', color=(194, 132, 69), size=14)

    def draw_shop(self):
        s = self.screen
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((27, 18, 43, 205))
        s.blit(shade, (0, 0))
        self.buttons = []
        # 金色展柜与红色帷幕沿用参考图的陈列形式。
        panel(s, (100, 84, 1080, 650), (105, 57, 47), radius=30)
        panel(s, (94, 76, 1092, 650), (224, 173, 100), (255, 225, 160), 30)
        panel(s, (107, 89, 1066, 624), (255, 237, 198), (185, 125, 73), 23)
        panel(s, (128, 109, 240, 67), (102, 66, 66), (231, 185, 119), 19)
        self.art.sprite(s, 'currency', (164, 141), (48, 48))
        text(s, self.profile.stars, (201, 111), 31, WHITE, bold=True)
        text(s, '我的星声', (203, 151), 13, (239, 211, 185))
        text(s, '星声商店', (640, 126), 33, (103, 59, 49), True, True)
        text(s, '选择一位伙伴，一起守护云端花园', (640, 169), 16, (151, 103, 77), True)
        self.button((1085, 108, 64, 50), '关闭', 'shop', color=(205, 102, 79), size=17)
        for i, (key, character) in enumerate(CHARACTERS.items()):
            left = 139 + i * 338
            center = left + 162
            owned = key in self.profile.owned
            active = key == self.profile.selected
            border = (126, 169, 126) if active else (218, 163, 88)
            panel(s, (left, 202, 324, 435), (245, 211, 157), border, 16)
            panel(s, (left + 9, 210, 306, 286), (126, 53, 65), radius=12)
            for stripe in range(12):
                stripe_x = left + 12 + stripe * 25
                pygame.draw.rect(s, (158 + stripe % 2 * 13, 61, 76), (stripe_x, 212, 24, 275))
            # 中央柔和灯光与帷幕侧翼，让未兑换角色也能看清立绘。
            pygame.draw.ellipse(s, (210, 139, 128), (left + 50, 239, 224, 235))
            pygame.draw.ellipse(s, (167, 102, 91), (left + 64, 466, 196, 20))
            self.art.sprite(s, key, (center, 360), (235, 245))
            pygame.draw.polygon(s, (183, 64, 76), [(left + 10, 211), (left + 78, 211), (left + 31, 292), (left + 10, 327)])
            pygame.draw.polygon(s, (183, 64, 76), [(left + 314, 211), (left + 246, 211), (left + 293, 292), (left + 314, 327)])
            pygame.draw.line(s, (249, 207, 121), (left + 10, 292), (left + 37, 278), 4)
            pygame.draw.line(s, (249, 207, 121), (left + 314, 292), (left + 287, 278), 4)
            badge = '使用中' if active else ('已拥有' if owned else '可兑换')
            panel(s, (left + 226, 220, 78, 26), (108, 144, 113) if owned else (110, 64, 70), radius=12)
            text(s, badge, (left + 265, 232), 13, WHITE, True)
            text(s, character['name'], (center, 514), 24, (102, 57, 47), True, True)
            text(s, character['title'], (center, 548), 16, (157, 101, 68), True)
            if owned:
                status = '免费初始伙伴' if character['price'] == 0 else '永久拥有'
                text(s, status, (center, 577), 15, (113, 131, 88), True)
                self.button((left + 43, 594, 238, 34), '正在守护' if active else '使用角色', f'equip:{key}', not active, color=(104, 151, 119), size=16)
            else:
                self.art.sprite(s, 'currency', (center - 51, 576), (25, 25))
                text(s, f'{character["price"]} 星声', (center + 13, 577), 17, (124, 87, 83), True, True)
                affordable = self.profile.stars >= character['price']
                self.button((left + 43, 594, 238, 34), '兑换角色' if affordable else '星声不足', f'buy:{key}', affordable, color=(192, 126, 59), size=16)
        text(s, self.shop_notice, (640, 660), 16, (116, 75, 58), True)
        text(s, f'每关首次通关 +{FIRST_CLEAR_STARS} 星声  ·  已首通 {len(self.profile.cleared)}/{len(LEVEL_NAMES)}  ·  兑换与选择自动保存', (640, 692), 14, (157, 114, 79), True)

    def draw_settings(self):
        s = self.screen
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((29, 21, 49, 188))
        s.blit(shade, (0, 0))
        self.buttons = []
        panel(s, (410, 220, 460, 355), (254, 245, 251), (220, 189, 230), 23)
        text(s, '声音设置', (640, 266), 29, PLUM, True, True)
        for y, key, title, description in [
            (315, 'music', '背景音乐', '循环播放关卡配乐'),
            (394, 'effects', '音效', '操作、建塔和受击提示'),
        ]:
            panel(s, (445, y - 8, 390, 64), (240, 225, 246), radius=13)
            text(s, title, (463, y), 17, PLUM, bold=True)
            text(s, description, (463, y + 25), 13, MUTED)
            enabled = self.audio.settings[key]
            self.button((715, y + 2, 100, 38), '开启' if enabled else '关闭',
                        f'audio:{key}', color=TEAL if enabled else (117, 100, 137), size=16)
        if self.settings_notice:
            text(s, self.settings_notice, (640, 473), 13, MUTED, True)
        elif self.browser:
            message = '进度保存在此浏览器，清理网站数据会清除存档。'
            if not getattr(self.progress, 'persistent', True):
                message = '浏览器存储不可用，本次进度将在关闭后丢失。'
            text(s, message, (640, 473), 13, MUTED, True)
        self.button((543, 508, 194, 38), '返回游戏 [Esc]', 'settings', size=16)

    def draw(self):
        s, g = self.screen, self.game
        s.blit(self.art.map, (0, 0))
        for obstacle in g.obstacles:
            self.art.draw_obstacle(s, obstacle, obstacle is g.priority_target, theme=g.layout['theme'])
        self.draw_selection()
        self.buttons = []
        for tower in g.towers:
            x, y = tower.position
            pygame.draw.ellipse(s, (140, 112, 163), (x - 25, y + 18, 50, 14))
            if tower.aura_radius:
                pygame.draw.ellipse(s, (255, 208, 85), (x - 29, y + 14, 58, 20), 3)
            kick = 6 * tower.recoil / tower.RECOIL_TIME
            self.art.turret(s, tower.kind, (x, y), tower.aim_angle, kick)
            if g.attack_speed_for(tower) > 1:
                text(s, '+25%', (x, y - 36), 13, (255, 245, 153), True, True)
            for i in range(tower.level):
                star(s, (x + (i - (tower.level - 1) / 2) * 12, y + 32), 5, (255, 235, 147))
        hx, hy = g.path[-1]
        pygame.draw.ellipse(s, (157, 129, 179), (hx - 55, hy - 6, 110, 25))
        key = portrait_key(self.profile.selected, g.lives)
        self.art.sprite(s, key, (hx, hy + 10 + math.sin(self.tick * 2) * 2), (153, 185), feet=True)
        panel(s, (hx - 45, hy + 24, 90, 30), (255, 240, 250), (223, 174, 210), 14)
        text(s, f'生命 {g.lives}', (hx, hy + 38), 17, (198, 91, 130), True, True)
        for enemy in g.enemies:
            if enemy.kind == 'boss':
                self.art.draw_boss(s, enemy, self.tick)
            else:
                draw_enemy(s, enemy, self.tick, self.art)
        self.draw_target()
        for tower in g.towers:
            if g.waves.active and tower.kind == 'magic' and tower.beam_active:
                draw_laser(s, tower.position, tower.beam_target.position, self.tick)
        for effect in g.effects:
            draw_effect(s, effect, self.tick, self.art)
        self.draw_hud()
        self.draw_boss_hud()
        self.draw_popup()
        if self.settings_open:
            self.draw_settings()
        elif self.shop:
            self.draw_shop()
        elif self.menu or g.state != 'playing':
            self.draw_modal()
        if not self.started:
            self.buttons = []
            shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            shade.fill((30, 22, 48, 210))
            s.blit(shade, (0, 0))
            panel(s, (370, 235, 540, 330), (255, 244, 252), (222, 190, 231), 28)
            text(s, '保卫大肥鱼', (640, 292), 40, PLUM, True, True)
            text(s, '十段旅程，和伙伴一起守护花园', (640, 354), 20, MUTED, True)
            self.button((490, 405, 300, 62), '点击开始冒险', 'begin', size=25)
            message = '推荐横屏游玩 · 点击空地建塔 · 进度自动保存在此浏览器'
            if not getattr(self.progress, 'persistent', True):
                message = '浏览器存储不可用，本次进度仅在当前页面保留。'
            text(s, message, (640, 513), 15, MUTED, True)
        pygame.display.flip()

    def draw_boss_hud(self):
        boss = self.game.boss
        if boss is None:
            return
        s = self.screen
        panel(s, (300, 102, 680, 47), (66, 38, 69), (247, 166, 99), 16)
        title = 'BOSS 登场！' if self.game.boss_intro > 0 else '最终 BOSS'
        text(s, f'{title}  {boss.name}', (320, 108), 17, (255, 214, 147), bold=True)
        text(s, '抵达终点扣 10 生命', (754, 111), 13, (255, 201, 202))
        pygame.draw.rect(s, (101, 65, 91), (320, 134, 640, 7), border_radius=3)
        pygame.draw.rect(s, (246, 132, 96), (320, 134, round(640 * boss.hp / boss.max_hp), 7), border_radius=3)
        text(s, f'{math.ceil(boss.hp)} / {math.ceil(boss.max_hp)}', (640, 118), 14, WHITE, True)

    def draw_target(self):
        target = self.game.priority_target
        if target is None or target.status != 'alive':
            return
        x, y = target.position
        color = (239, 78, 125)
        radius = max(30, getattr(target, 'hit_radius', 24) + 6)
        pygame.draw.circle(self.screen, WHITE, (x, y), radius, 4)
        pygame.draw.circle(self.screen, color, (x, y), radius, 2)
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            pygame.draw.line(self.screen, color, (x + dx * (radius - 7), y + dy * (radius - 7)),
                             (x + dx * (radius + 7), y + dy * (radius + 7)), 3)
        pygame.draw.polygon(self.screen, color, [(x, y - radius - 19), (x - 7, y - radius - 30), (x + 7, y - radius - 30)])
        label = f'优先攻击 {getattr(target, "name", "怪兽")}  {math.ceil(target.hp)}/{target.max_hp:g}   ·   右键取消'
        top = 151 if self.game.boss else 103
        panel(self.screen, (420, top, 445, 30), (255, 239, 247), radius=12)
        text(self.screen, label, (642, top + 15), 14, PLUM, True)

    def action(self, action):
        g = self.game
        if action == 'begin':
            self.started = True
            self.audio.unlock()
            return
        if action == 'cancel':
            self.selected = self.build_pad = None
            g.priority_target = None
            return
        if action not in TOWERS:
            self.audio.effect('tap')
        if action == 'settings':
            self.settings_open = not self.settings_open
            self.settings_notice = ''
        elif action.startswith('audio:') and self.settings_open:
            key = action.split(':', 1)[1]
            enabled = not self.audio.settings[key]
            try:
                self.progress.set_audio_setting(key, enabled)
            except SAVE_ERRORS:
                self.settings_notice = '设置未能保存，请稍后重试。'
            else:
                self.audio.set_enabled(key, enabled)
                self.settings_notice = ''
        elif action == 'shop':
            self.shop = not self.shop
            self.selected = self.build_pad = None
            if self.shop:
                try:
                    self.profile = self.progress.snapshot()
                    self.shop_notice = '兑换后点击使用角色，就能与她一起冒险。'
                except SAVE_ERRORS:
                    self.shop_notice = '存档暂不可用，请稍后重新打开商店。'
        elif action.startswith(('buy:', 'equip:')):
            self.shop_action(action)
        elif action == 'reward':
            self.settle_victory()
        elif action in TOWERS and self.build_pad is not None:
            if g.build(action, self.build_pad):
                self.audio.effect('build')
                self.selected = g.towers[-1]
                self.build_pad = None
                self.notice = '建造成功。点击防御塔可升级或出售，右键取消选择。'
        elif action == 'menu':
            self.menu = not self.menu
            self.selected = self.build_pad = None
        elif action == 'restart':
            self.reset(g.level)
        elif action.startswith('level:'):
            self.reset(int(action.split(':')[1]))
        elif action == 'next':
            self.reset(g.level + 1)
        elif action == 'pause':
            self.paused = not self.paused
        elif action == 'speed':
            self.speed = 3 - self.speed
        elif action == 'wave' and g.state == 'playing':
            if g.waves.start():
                self.paused = False
                self.selected = self.build_pad = None
                self.notice = ('最终波！手柄大魔王即将登场，请升级防御塔。'
                               if 'boss' in g.waves.queue else
                               '敌群来袭！击杀获得金币，随时点击空地补充防御。')
        elif action == 'upgrade' and self.selected:
            g.upgrade(self.selected)
        elif action == 'sell' and self.selected:
            g.sell(self.selected)
            self.selected = None

    def shop_action(self, action):
        operation, key = action.split(':', 1)
        if not self.shop or key not in CHARACTERS:
            return
        try:
            if operation == 'buy':
                result = self.progress.purchase(key)
                messages = {'purchased': '兑换成功！点击使用角色即可切换。',
                            'owned': '已经拥有这位伙伴，可以直接使用。',
                            'insufficient': '星声不足，首次通关可以获得更多星声。'}
                self.shop_notice = messages[result]
            elif self.progress.select(key):
                self.shop_notice = f'已选择 {CHARACTERS[key]["name"]}，正在地图上等你！'
            else:
                self.shop_notice = '请先兑换这位伙伴。'
            self.profile = self.progress.snapshot()
        except SAVE_ERRORS:
            self.shop_notice = '存档暂不可用，请重试本次操作。'

    def settle_victory(self):
        if self.game.state != 'won' or self.reward_settled:
            return
        try:
            reward = self.progress.record_victory(self.game.level)
            self.profile = self.progress.snapshot()
            self.reward_message = f'首次通关！获得 {reward} 星声' if reward else '本关首通星声已领取'
            self.reward_settled = True
        except SAVE_ERRORS:
            self.reward_message = '星声存档暂不可用，请点击重试'

    def advance(self, dt):
        self.audio.update()
        if not self.started or self.paused or self.menu or self.shop or self.settings_open:
            return
        if self.game.waves.active:
            self.tick += dt
        hits = 0
        remaining = dt * self.speed
        while remaining > 1e-9:
            step = min(remaining, 1 / 60)
            hits += self.game.update(step)
            remaining -= step
        if hits:
            self.audio.hit(hits)
        if self.game.state == 'won' and not self.reward_settled and not self.reward_message:
            self.settle_victory()

    def handle_event(self, event):
        if self.browser:
            if event.type == pygame.WINDOWFOCUSLOST:
                if self.game.waves.active:
                    self.paused = True
                self.audio.clear_hits()
            if event.type == pygame.FINGERDOWN:
                self.pointer = (round(event.x * WIDTH), round(event.y * HEIGHT))
                event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=self.pointer)
            elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION):
                if getattr(event, 'touch', False):
                    return  # FINGERDOWN 已处理，避免触摸合成的鼠标事件重复购买。
                self.pointer = event.pos
        if not self.started:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for rect, action, enabled in self.buttons:
                    if action == 'begin' and rect.collidepoint(event.pos):
                        self.action('begin')
                        break
            return
        if event.type == pygame.KEYDOWN:
            if self.settings_open:
                if event.key == pygame.K_ESCAPE:
                    self.action('settings')
                return
            if self.shop:
                if event.key == pygame.K_ESCAPE:
                    self.action('shop')
                return
            if event.key == pygame.K_ESCAPE:
                if self.menu:
                    self.menu = False
                elif self.selected is not None or self.build_pad is not None:
                    self.selected = self.build_pad = None
                elif self.game.priority_target is not None:
                    self.game.priority_target = None
                elif self.game.state == 'playing':
                    self.action('pause')
            elif not self.menu and self.game.state == 'playing':
                actions = {pygame.K_SPACE: 'wave', pygame.K_p: 'pause', pygame.K_1: 'bottle',
                           pygame.K_2: 'moon', pygame.K_3: 'arrow', pygame.K_4: 'star',
                           pygame.K_5: 'sun', pygame.K_6: 'magic', pygame.K_7: 'fan',
                           pygame.K_8: 'rocket'}
                if event.key in actions:
                    self.action(actions[event.key])
            return
        if event.type != pygame.MOUSEBUTTONDOWN:
            return
        position = event.pos
        if event.button == 3:
            if self.shop or self.settings_open:
                return
            self.selected = self.build_pad = None
            self.game.priority_target = None
            return
        if event.button != 1:
            return
        for rect, action, enabled in reversed(self.buttons):
            if rect.collidepoint(position):
                if enabled:
                    self.action(action)
                elif action in TOWERS:
                    self.notice = '金币不足，击退更多敌人后再来建造。'
                return
        if self.shop or self.menu or self.settings_open or self.game.state != 'playing':
            return
        if self.popup and self.popup.collidepoint(position):
            return
        if self.game.select_target_at(position):
            self.selected = self.build_pad = None
            self.notice = '射程内优先攻击标记对象；右键取消，目标死亡后自动解除。'
            return
        pad = pad_at(position)
        self.selected = self.build_pad = None
        if pad is None:
            return
        self.selected = next((t for t in self.game.towers if t.pad == pad), None)
        if self.selected:
            return
        if self.game.can_build(pad):
            self.build_pad = pad
            self.notice = '建塔快捷键：1 瓶子 / 2 月亮 / 3 弓箭 / 4 星星 / 5 太阳 / 6 魔法球 / 7 风扇 / 8 火箭。'
        else:
            cell = (pad % COLS, pad // COLS)
            if cell in self.game.layout['home_cells']:
                self.notice = f'这里是{CHARACTERS[self.profile.selected]["name"]}的家，请在周围布置防御。'
            elif cell in self.game.layout['path_cells']:
                self.notice = '这是怪兽经过的道路，请在路边的空地建造。'
            elif self.game.layout['theme'] == 'bay':
                self.notice = '请在冰岛上的空地建造炮塔。'

    def run(self, screenshot=None, preview_menu=False, preview_shop=False, preview_boss=False):
        if screenshot:
            if preview_boss:
                self.reset(9)
                self.game.waves.index = len(self.game.config['waves']) - 1
                self.game.waves.active = True
                boss = Enemy('boss', self.game.config['hp_scale'], self.game.path)
                boss.position.update(self.game.path[2])
                boss.next_waypoint = 3
                self.game.enemies = [boss]
                self.game.boss_intro = 4
                self.game.priority_target = boss
                self.notice = '最终波！手柄大魔王登场，点击它让炮塔优先集火。'
            if preview_menu:
                self.build_pad = min((pad for pad in range(len(PADS)) if self.game.can_build(pad)),
                                     key=lambda pad: pygame.Vector2(PADS[pad]).distance_squared_to((416, 352)))
            if preview_shop:
                self.action('shop')
            self.draw()
            pygame.image.save(self.screen, str(screenshot))
            self.progress.close()
            pygame.quit()
            return
        self.draw()
        running = True
        while running:
            dt = min(self.clock.tick(60) / 1000, .1)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    self.handle_event(event)
                    if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                        self.draw()
            self.advance(dt)
            self.draw()
        self.progress.close()
        pygame.quit()

    async def run_async(self):
        """每帧让出浏览器主线程；页面隐藏时冻结战斗，不补算离开期间的时间。"""
        from platform import window, document
        self.draw()
        window.gameReady = True
        try:
            while True:
                dt = min(self.clock.tick(60) / 1000, .1)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return
                    self.handle_event(event)
                if document.hidden:
                    if self.game.waves.active:
                        self.paused = True
                    self.audio.clear_hits()
                else:
                    self.advance(dt)
                    self.draw()
                await asyncio.sleep(0)
        finally:
            self.progress.close()
            pygame.quit()


async def browser_main():
    try:
        app = App(browser=True)
        app.reset(0)
        await app.run_async()
    except Exception:
        from platform import window
        window.gameLoadError = '游戏加载失败，请刷新重试；若仍失败，请检查网络。'
        raise


if sys.platform == 'emscripten':
    asyncio.run(browser_main())
elif __name__ == '__main__':
    parser = argparse.ArgumentParser(description='保卫大肥鱼')
    parser.add_argument('--screenshot', type=Path, help='保存开局截图并退出')
    parser.add_argument('--preview-menu', action='store_true', help='截图中展示空地建造菜单')
    parser.add_argument('--preview-shop', action='store_true', help='截图中展示角色商店')
    parser.add_argument('--preview-boss', action='store_true', help='截图中展示最终 Boss（不修改存档）')
    parser.add_argument('--level', type=int, choices=range(1, 11), default=1, help='从指定关卡启动（1～10）')
    args = parser.parse_args()
    preview_progress = ProgressStore(':memory:') if args.screenshot else None
    app = App(progress=preview_progress)
    app.reset(args.level - 1)
    app.run(args.screenshot, args.preview_menu, args.preview_shop, args.preview_boss)
