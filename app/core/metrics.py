from prometheus_client import Counter, Histogram

# Define all operational Prometheus metrics in an isolated module to prevent circular imports

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests received",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)

HTTP_EXCEPTIONS_TOTAL = Counter(
    "http_exceptions_total",
    "Total HTTP exceptions raised",
    ["method", "path", "exception_type"],
)

ACTIVE_BORROWINGS = Counter("active_borrowings_total", "Total active checkout operations count")

ACTIVE_RESERVATIONS = Counter(
    "active_reservations_total", "Total active reservation operations count"
)

RESERVATION_PROMOTIONS_TOTAL = Counter(
    "reservation_promotions_total", "Total reservations promoted count"
)

DASHBOARD_REQUESTS_TOTAL = Counter(
    "dashboard_requests_total", "Total dashboard fetch requests count"
)
