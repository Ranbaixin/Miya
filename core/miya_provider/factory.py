"""
Miya Provider Factory
工厂模式创建Provider
"""

from .provider_manager import ProviderManager, get_provider_manager


class ProviderFactory:
    """Provider 工厂"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_provider(self, provider_id: str = None):
        """获取Provider实例"""
        manager = get_provider_manager()
        if provider_id:
            return manager.get_provider_by_id(provider_id)
        return manager.curr_provider

    def chat(self, prompt: str, **kwargs):
        """简便聊天接口"""
        manager = get_provider_manager()
        return manager.chat(prompt, **kwargs)


def get_provider_factory() -> ProviderFactory:
    """获取Provider工厂实例"""
    return ProviderFactory()


__all__ = ["ProviderFactory", "get_provider_factory"]
