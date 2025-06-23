'''
Exporter of the architecture.
'''

from abc import ABC, abstractmethod


class Exporter(ABC):
    """Abstract class representing an exporter."""

    @abstractmethod
    def __init__(self, arch) -> None:
        """Create an exporter for the architecture `arch`."""
        self.arch = arch

    @abstractmethod
    def export(self):
        """Export the architecture."""
