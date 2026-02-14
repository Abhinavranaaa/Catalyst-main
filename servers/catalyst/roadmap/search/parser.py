class QueryParser:
    DEFAULT_LIMIT = 6
    DEFAULT_OFFSET = 0
    def parse(self,payload:dict):
        return {
            "search": payload.get("search"),
            "filters": payload.get("filters", {}),
            "sort": payload.get("sort", []),
            "limit":payload.get("limit",self.DEFAULT_LIMIT),
            "offset":payload.get("offset",self.DEFAULT_OFFSET)

        }

    
