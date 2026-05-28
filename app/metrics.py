from prometheus_client import Counter, Gauge

# --- Telemetry ---
telemetry_requests_total = Counter(
    "telemetry_requests_total",
    "Total number of telemetry requests received from chargers"
)

# --- Validation ---
validation_failures_total = Counter(
    "validation_failures_total",
    "Total number of OCPP validation failures"
)

validation_success_total = Counter(
    "validation_success_total",
    "Total number of successful OCPP validations"
)

# --- OTA ---
ota_triggered_total = Counter(
    "ota_triggered_total",
    "Total number of OTA updates triggered"
)

ota_success_total = Counter(
    "ota_success_total",
    "Total number of successful OTA updates"
)

ota_failed_total = Counter(
    "ota_failed_total",
    "Total number of failed OTA updates"
)

# --- Charger States ---
chargers_online = Gauge(
    "chargers_online",
    "Number of chargers currently in CONFIG_SUCCESS state"
)

chargers_pending_ota = Gauge(
    "chargers_pending_ota",
    "Number of chargers currently in INTEGRATION_STARTED state"
)