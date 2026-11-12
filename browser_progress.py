"""浏览器本地存档；接口与桌面 SQLite 后端一致，写入失败不修改状态。"""
import json
from config import CHARACTERS, INITIAL_STARS, FIRST_CLEAR_STARS, LEVEL_NAMES
from progress import Profile


class MemoryStorage:
    """存储被浏览器禁用时仍能游玩本次会话，也用于离线单元测试。"""
    def __init__(self):
        self.values = {}

    def getItem(self, key):
        return self.values.get(key)

    def setItem(self, key, value):
        self.values[key] = value


class BrowserProgressStore:
    KEY = 'defend-big-fish.save.v1'
    persistent = True

    def __init__(self, storage=None):
        if storage is None:
            from platform import window
            try:
                storage = window.localStorage
            except Exception as error:
                raise OSError('浏览器不允许保存进度') from error
        self.storage = storage
        self._load()
        # 浏览器可能允许读取却禁止写入，先用独立探针验证，不覆盖玩家数据。
        try:
            storage.setItem(self.KEY + '.probe', '1')
            if hasattr(storage, 'removeItem'):
                storage.removeItem(self.KEY + '.probe')
        except Exception as error:
            raise OSError('浏览器不允许保存进度') from error

    @staticmethod
    def initial():
        return dict(version=1, stars=INITIAL_STARS, owned=['whale'], selected='whale',
                    cleared=[], audio={'music': True, 'effects': True})

    def _load(self):
        try:
            raw = self.storage.getItem(self.KEY)
            if raw is None or str(raw) in ('undefined', 'null'):
                return self.initial()
            data = json.loads(str(raw))
            assert type(data) is dict and data['version'] == 1
            assert type(data['stars']) is int and data['stars'] >= 0
            assert type(data['owned']) is list and all(k in CHARACTERS for k in data['owned'])
            assert 'whale' in data['owned'] and data['selected'] in data['owned']
            assert type(data['cleared']) is list
            assert all(type(n) is int and 0 <= n < len(LEVEL_NAMES) for n in data['cleared'])
            assert all(type(data['audio'][k]) is bool for k in ('music', 'effects'))
            return data
        except Exception as error:
            raise OSError('无法读取浏览器存档') from error

    def _save(self, data):
        try:
            self.storage.setItem(self.KEY, json.dumps(data, ensure_ascii=False))
        except Exception as error:
            raise OSError('存档写入失败') from error

    def snapshot(self):
        data = self._load()
        return Profile(data['stars'], frozenset(data['owned']), data['selected'], frozenset(data['cleared']))

    def purchase(self, character):
        if character not in CHARACTERS:
            return 'unknown'
        data = self._load()
        if character in data['owned']:
            return 'owned'
        price = CHARACTERS[character]['price']
        if data['stars'] < price:
            return 'insufficient'
        data['stars'] -= price
        data['owned'].append(character)
        self._save(data)
        return 'purchased'

    def select(self, character):
        data = self._load()
        if character not in CHARACTERS or character not in data['owned']:
            return False
        data['selected'] = character
        self._save(data)
        return True

    def record_victory(self, level):
        if type(level) is not int or not 0 <= level < len(LEVEL_NAMES):
            raise ValueError('关卡不存在')
        data = self._load()
        if level in data['cleared']:
            return 0
        data['cleared'].append(level)
        data['stars'] += FIRST_CLEAR_STARS
        self._save(data)
        return FIRST_CLEAR_STARS

    def audio_settings(self):
        return self._load()['audio'].copy()

    def set_audio_setting(self, key, enabled):
        if key not in ('music', 'effects'):
            raise ValueError('未知音频设置')
        data = self._load()
        data['audio'][key] = bool(enabled)
        self._save(data)

    def close(self):
        pass  # 每次操作已立即保存，不依赖不可靠的网页关闭回调。
