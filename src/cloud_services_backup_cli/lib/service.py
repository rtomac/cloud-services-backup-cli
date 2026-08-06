from abc import ABC, abstractmethod

from .util import error_invalid_subcommand, print_usage


REGISTRY = {}


def register_service(slug: str):
    def wrapper(cls):
        REGISTRY[slug] = cls
        cls.service_slug = slug
        return cls
    return wrapper

def resolve_service(slug: str) -> type:
    return REGISTRY[slug]

class Service(ABC):
    def __init__(self, username: str):
        self.username = username

    @classmethod
    def help(cls) -> None:
        print_usage(cls.__doc__)

    @classmethod
    def authorize(cls, payload: str = None) -> None:
        error_invalid_subcommand("authorize")

    @abstractmethod
    def info(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    def setup(self, *args: str) -> None:
        raise NotImplementedError()

    @abstractmethod
    def setup_required(self) -> bool:
        raise NotImplementedError()

    def copy(self, *args: str) -> None:
        self.backup("copy", *args)

    def sync(self, *args: str) -> None:
        self.backup("sync", *args)

    def backup(self, subcommand: str, *args: str) -> None:
        if self.setup_required():
            self.setup(*args)
        self._backup(subcommand, *args)

    @abstractmethod
    def _backup(self, subcommand: str, *args: str) -> None:
        raise NotImplementedError()
