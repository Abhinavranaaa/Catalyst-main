import logging
from catalyst.constants import ALLOWED_OPERATORS
from django.db.models import Q, JSONField
from django.contrib.postgres.fields import ArrayField



logger = logging.getLogger(__name__)
class DynamicFilterApplier:
    OPERATOR_MAP = ALLOWED_OPERATORS

    def apply(self,qs,filters,filter_map):
        model = qs.model
        for field,condition in filters.items():
            orm_field = filter_map.get(field)
            if not orm_field:
                logger.warning('no matching field found in the system inventory')
                continue
            is_array = is_array_field(model,orm_field)
            if isinstance(condition,dict):
                for op,value in condition.items():
                    if not op in self.OPERATOR_MAP:
                        continue
                    lookup = orm_field+self.OPERATOR_MAP[op]
                    qs = qs.filter(**{lookup: value})
            
            elif isinstance(condition,list):
                if is_array:
                    for value in condition:
                        qs = qs.filter(**{f"{orm_field}__contains": [value]})
                else:
                    qs=qs.filter(**{f"{orm_field}__in": condition})

            else:
                qs = qs.filter(**{orm_field: condition})

        return qs.distinct()


def is_array_field(model,field_name):
    try:
        field = model._meta.get_field(field_name)
        return isinstance(field,(ArrayField,JSONField))
    except Exception:
        logger.warning('field check returned an exception')
        return False

