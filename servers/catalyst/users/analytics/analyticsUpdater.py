from abc import ABC, abstractmethod
class AnalyticsUpdater(ABC):
    @abstractmethod
    def update(self,user_id,attempts):
        pass
