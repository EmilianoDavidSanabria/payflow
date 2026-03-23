from math import ceil

from rest_framework import status

from core.api_errors import error_response


def paginate_queryset(queryset, request):
    page = request.query_params.get("page", "1")
    page_size = request.query_params.get("page_size", "10")

    try:
        page = int(page)
        page_size = int(page_size)
    except ValueError:
        return None, error_response(
            "page and page_size must be integers",
            status.HTTP_400_BAD_REQUEST,
        )

    if page < 1:
        return None, error_response(
            "page must be greater than or equal to 1",
            status.HTTP_400_BAD_REQUEST,
        )

    if page_size < 1 or page_size > 100:
        return None, error_response(
            "page_size must be between 1 and 100",
            status.HTTP_400_BAD_REQUEST,
        )

    count = queryset.count()
    total_pages = ceil(count / page_size) if count > 0 else 1

    start = (page - 1) * page_size
    end = start + page_size

    return {
        "page": page,
        "page_size": page_size,
        "count": count,
        "total_pages": total_pages,
        "results": queryset[start:end],
    }, None