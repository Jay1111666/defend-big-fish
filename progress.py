"""持久化星声、已兑换角色、当前角色与首通记录。"""
from dataclasses import dataclass
from pathlib import Path
import sqlite3
import sys
from config import CHARACTERS, INITIAL_STARS, FIRST_CLEAR_STARS, LEVEL_NAMES


def default_save_path():
    # 所有 exe 版本共用同目录存档，资源解压目录只用于读取美术。
    root = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
    return root / 'saves' / 'progress.sqlite3'


@dataclass(frozen=True)
class Profile:
    stars: int
    owned: frozenset
    selected: str
    cleared: frozenset


class ProgressStore:
    def __init__(self, path=None):
        self.path = default_save_path() if path is None else path
        if str(self.path) != ':memory:':
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, timeout=5)
        self.connection.execute('PRAGMA foreign_keys = ON')
        try:
            with self.connection:
                self.connection.execute('BEGIN IMMEDIATE')
                self.connection.execute('CREATE TABLE IF NOT EXISTS owned (character TEXT PRIMARY KEY)')
                self.connection.execute('''CREATE TABLE IF NOT EXISTS profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    stars INTEGER NOT NULL CHECK (stars >= 0),
                    selected TEXT NOT NULL REFERENCES owned(character))''')
                self.connection.execute('CREATE TABLE IF NOT EXISTS cleared (level INTEGER PRIMARY KEY)')
                self.connection.execute('''CREATE TABLE IF NOT EXISTS audio_settings (
                    name TEXT PRIMARY KEY, enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)))''')
                self.connection.execute("INSERT OR IGNORE INTO owned VALUES ('whale')")
                self.connection.execute("INSERT OR IGNORE INTO profile VALUES (1, ?, 'whale')", (INITIAL_STARS,))
        except sqlite3.Error:
            self.connection.close()
            raise

    def snapshot(self):
        # 多个窗口同时运行时，余额和拥有记录仍来自同一数据库快照。
        with self.connection:
            self.connection.execute('BEGIN')
            stars, selected = self.connection.execute('SELECT stars, selected FROM profile WHERE id = 1').fetchone()
            owned = frozenset(row[0] for row in self.connection.execute('SELECT character FROM owned'))
            cleared = frozenset(row[0] for row in self.connection.execute('SELECT level FROM cleared'))
        return Profile(stars, owned, selected, cleared)

    def purchase(self, character):
        if character not in CHARACTERS:
            return 'unknown'
        # 在同一写事务内检查、扣款和解锁，连点或多个窗口不会重复扣款。
        with self.connection:
            self.connection.execute('BEGIN IMMEDIATE')
            if self.connection.execute('SELECT 1 FROM owned WHERE character = ?', (character,)).fetchone():
                return 'owned'
            price = CHARACTERS[character]['price']
            balance = self.connection.execute('SELECT stars FROM profile WHERE id = 1').fetchone()[0]
            if balance < price:
                return 'insufficient'
            self.connection.execute('UPDATE profile SET stars = stars - ? WHERE id = 1', (price,))
            self.connection.execute('INSERT INTO owned VALUES (?)', (character,))
        return 'purchased'

    def select(self, character):
        if character not in CHARACTERS:
            return False
        with self.connection:
            self.connection.execute('BEGIN IMMEDIATE')
            if not self.connection.execute('SELECT 1 FROM owned WHERE character = ?', (character,)).fetchone():
                return False
            self.connection.execute('UPDATE profile SET selected = ? WHERE id = 1', (character,))
        return True

    def record_victory(self, level):
        if type(level) is not int or not 0 <= level < len(LEVEL_NAMES):
            raise ValueError('关卡不存在')
        with self.connection:
            self.connection.execute('BEGIN IMMEDIATE')
            inserted = self.connection.execute('INSERT OR IGNORE INTO cleared VALUES (?)', (level,)).rowcount
            if not inserted:
                return 0
            self.connection.execute('UPDATE profile SET stars = stars + ? WHERE id = 1', (FIRST_CLEAR_STARS,))
        return FIRST_CLEAR_STARS

    def audio_settings(self):
        settings = {'music': True, 'effects': True}
        for key, enabled in self.connection.execute('SELECT name, enabled FROM audio_settings'):
            if key in settings:
                settings[key] = bool(enabled)
        return settings

    def set_audio_setting(self, key, enabled):
        if key not in ('music', 'effects'):
            raise ValueError('未知音频设置')
        with self.connection:
            self.connection.execute(
                'INSERT INTO audio_settings VALUES (?, ?) ON CONFLICT(name) DO UPDATE SET enabled=excluded.enabled',
                (key, int(enabled)))

    def close(self):
        self.connection.close()
