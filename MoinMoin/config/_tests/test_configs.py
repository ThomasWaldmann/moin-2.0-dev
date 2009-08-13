from MoinMoin.config.multiconfig import DefaultConfig
from MoinMoin.storage.backends import create_simple_mapping


_tests = [DefaultConfig, ]

class TestConfigs:
    def testConfigs(self):
        for cls in _tests:
            cls.data_dir = self.request.cfg.data_dir
            cls.secrets = self.request.cfg.secrets
            cls.namespace_mapping = create_simple_mapping('memory:')

            # quite a bad hack to make _importPlugin succeed
            cls('MoinMoin')
