from abc import ABC, abstractmethod


REGISTRY = {}


def register_service(slug: str):
    def wrapper(cls):
        REGISTRY[slug] = cls
        return cls
    return wrapper

def resolve_service(slug: str) -> type:
    return REGISTRY[slug]

def get_service_usage(service_type: type) -> str:
    return service_type.__doc__.strip()


class Service(ABC):
    def __init__(self, username: str):
        self.username = username

    @abstractmethod
    def info(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    def setup(self, *args: str) -> None:
        raise NotImplementedError()

    def copy(self, *args: str) -> None:
        self.backup("copy", *args)

    def sync(self, *args: str) -> None:
        self.backup("sync", *args)

    def backup(self, subcommand: str, *args: str) -> None:
        if self._should_force_setup():
            self.setup(*args)
        self._backup(subcommand, *args)

    @abstractmethod
    def _should_force_setup(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def _backup(self, subcommand: str, *args: str) -> None:
        raise NotImplementedError()
