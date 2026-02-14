import logging


logger = logging.getLogger(__name__)
class DynamicSortApplier:

    def apply(self, qs, sort, sort_field_map, default_ordering=None):
        """
        qs: queryset
        sort: list of sort dicts from request
        sort_field_map: allowed sortable fields mapping
        default_ordering: fallback ordering list
        """

        ordering = []

        if not sort:
            logger.info('falling back to the default sort order')
            return qs.order_by(*default_ordering) if default_ordering else qs

        for s in sort:
            field = s.get("field")
            order = s.get("order", "asc")

            orm_field = sort_field_map.get(field)
            if not orm_field:
                logger.warning(
                    "Invalid sort field requested: %s", field
                )
                continue

            prefix = "-" if order == "desc" else ""
            ordering.append(prefix + orm_field)

        # fallback if nothing valid
        if not ordering and default_ordering:
            ordering = default_ordering

        return qs.order_by(*ordering)


