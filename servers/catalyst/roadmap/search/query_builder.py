from catalyst.constants import SORT_FIELD_MAP,FILTER_FIELD_MAP
from .filter import DynamicFilterApplier
from .sort import DynamicSortApplier
from .search import SearchDynamicQueries
from ..models import Roadmap

class QueryBuilder:

    def __init__(self,dynamic_filter:DynamicFilterApplier, sort: DynamicSortApplier, search:SearchDynamicQueries):
        self.dynamic_filter = dynamic_filter
        self.sort = sort
        self.search = search
        self.FILTER_FIELD_MAP = FILTER_FIELD_MAP
        self.SORT_FIELD_MAP = SORT_FIELD_MAP

    def build(self,user_id,validated_data:dict):

        qs = Roadmap.objects.filter(user_id=user_id)
        default_ordering = ["-modified_at"]
        if validated_data.get("search"):
            qs = self.search.buildFts(search_text=validated_data.get("search"),qs=qs)
            default_ordering = None
        
        if validated_data.get("filters"):
            qs = self.dynamic_filter.apply(qs=qs,filters=validated_data.get("filters"),filter_map=self.FILTER_FIELD_MAP)

        qs = self.sort.apply(qs=qs,sort=validated_data.get("sort"),sort_field_map=self.SORT_FIELD_MAP,default_ordering=default_ordering)

        limit = validated_data.get("limit")
        offset = validated_data.get("offset")
        qs = qs[offset: offset + limit]

        return qs
    


