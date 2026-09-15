"""D63 exact Google Calendar authenticated read connector identity."""

GOOGLE_CALENDAR_PLUGIN_ID = "google_calendar"
GOOGLE_CALENDAR_PLUGIN_VERSION = "1.0.0"
GOOGLE_CALENDAR_CAPABILITY_NAME = "upcoming_events"
GOOGLE_CALENDAR_ADAPTER_ID = "module.plugin.google_calendar"
GOOGLE_CALENDAR_OPERATION = "list_upcoming_events"
GOOGLE_CALENDAR_CAPABILITY_ID = "exec.plugin.google_calendar.upcoming_events"

GOOGLE_CALENDAR_CREDENTIAL_PROFILE_ID = "google_calendar.events.readonly"
GOOGLE_CALENDAR_CREDENTIAL_PROVIDER_ID = "google"
GOOGLE_CALENDAR_CREDENTIAL_AUTH_SCHEME = "oauth2_bearer"
GOOGLE_CALENDAR_CREDENTIAL_SCOPE = (
    "https://www.googleapis.com/auth/calendar.events.readonly"
)
GOOGLE_CALENDAR_CREDENTIAL_SECRET_REF = "google_calendar.access_token"

GOOGLE_CALENDAR_REQUEST_SENTINEL = "upcoming"
