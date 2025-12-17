"""
Exporter of the architecture.
"""

from abc import ABC, abstractmethod

import architecture


class Exporter(ABC):
    """Abstract class representing an exporter."""

    @abstractmethod
    def __init__(self, arch: architecture.Architecture) -> None:
        """Create an exporter for the architecture `arch`."""
        self.arch = arch

    @abstractmethod
    def export(self):
        """Export the architecture."""
