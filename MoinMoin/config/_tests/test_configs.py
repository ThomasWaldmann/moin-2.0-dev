from MoinMoin.config.multiconfig import DefaultConfig
from MoinMoin.storage.backends.memory import MemoryBackend


_tests = [DefaultConfig, ]

class TestConfigs:
    def testConfigs(self):
        for cls in _tests:
            cls.data_dir = self.request.cfg.data_dir
            cls.secrets = self.request.cfg.secrets
            cls.storage = MemoryBackend()
            cls.storage.user_backend = MemoryBackend()

            # quite a bad hack to make _importPlugin succeed
            cls('MoinMoin')
