
# default handling if nothing passed modify in sort as well
# create a view for the same and test the code before sleeping today also do dsa as well
from django.contrib.postgres.search import SearchQuery,SearchRank
from django.db.models import Q,F



class SearchDynamicQueries:

    def buildFts(self,search_text,qs):
        query_en = SearchQuery(search_text, config="english", search_type="websearch")
        query_simple = SearchQuery(search_text, config="simple")

        qs = qs.annotate(
            rank_en=SearchRank(F("search_vector_en"), query_en),
            rank_simple=SearchRank(F("search_vector_smpl"), query_simple),
            rank=F("rank_en") * 0.7 + F("rank_simple") * 0.3
        ).filter(
            Q(rank_en__gt=0.05) | Q(rank_simple__gt=0.05)
        ).order_by("-rank")

        return qs
    


    
    
    




