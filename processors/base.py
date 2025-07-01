
import os
import pandas as pd
from abc import ABC, abstractmethod

class ProcessingStep(ABC):
    """Abstract base class for a step in the video processing pipeline."""

    def __init__(self, entry, args):
        self.entry = entry
        self.args = args
        self.url = entry.get("youtube_url")
        self.base_name = entry.get("base_filename")

    @abstractmethod
    def process(self):
        """Executes the processing step. Returns the updated manifest entry."""
        pass

    @property
    @abstractmethod
    def is_complete(self):
        """Checks if this step has already been completed successfully."""
        pass

    def run(self):
        """Runs the step if it's not already complete or if forced."""
        if not self.args.force and self.is_complete:
            print(f"[CACHE] Skipping {self.__class__.__name__} for '{self.base_name}'")
            return self.entry

        print(f"[INFO] Running {self.__class__.__name__} for '{self.base_name}'...")
        return self.process()
