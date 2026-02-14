import logging
from catalyst.constants import ALLOWED_OPERATORS,ALLOWED_SORT_ORDERS
logger = logging.getLogger(__name__)

class QueryValidator:
    ALLOWED_OPERATORS = ALLOWED_OPERATORS
    ALLOWED_SORT_ORDERS = ALLOWED_SORT_ORDERS

    def validate(self,payload:dict):

        if not payload:
            logger.warning("payload is empty")
            return {}
        
        filters = payload.get('filters',{})
        for field,value in filters.items():
            if isinstance(value, dict):
                for op in value:
                    if op not in self.ALLOWED_OPERATORS:
                        raise ValueError(f"Invalid operator: {op}")
            
        
        for itr in payload.get('sort',[]):
            if isinstance(itr,dict):
                if itr['order'] not in self.ALLOWED_SORT_ORDERS:
                    raise ValueError(f"Invalid sort order: {itr['order']}")
        
        return payload
    
