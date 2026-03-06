from django.db import transaction
from ..service.dashboarCacheService import DashBoardCacheService

class AnalyticsCoordinator:

    def __init__(self, updaters,cache_service:DashBoardCacheService):
        self.updaters = updaters
        self.cache_service=cache_service

    # either all happens or none
    @transaction.atomic
    def process_attempt(self, user_id, attempts):
        for updater in self.updaters:
            updater.update(user_id, attempts)
        self.cache_service.invalidate(user_id)