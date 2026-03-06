from .dashboarCacheService import DashBoardCacheService
from .dashboardBuilder import DashboardBuilder
from practice.helper.DbHelper import fetch_daily_activity,fetch_user_stats
from catalyst.constants import HEATMAP_DAYS
class DashBoardReadService:
    def __init__(self,cache_service:DashBoardCacheService,builder:DashboardBuilder):
        self.cache_service=cache_service
        self.builder=builder

    def render(self,user_id):
        cached=self.cache_service.get(user_id)
        if cached:
            return cached
        daily_rows = fetch_daily_activity(user_id,HEATMAP_DAYS)
        stats = fetch_user_stats(user_id)
        response = self.builder.build(stats,daily_rows)
        self.cache_service.set(user_id,response)
        return response

        
