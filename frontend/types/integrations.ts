export type GoogleCalendarConnectionState =
  | "disconnected"
  | "active"
  | "reauthorization_required";

export interface GoogleCalendarIntegrationStatus {
  connector_enabled: boolean;
  configuration_present: boolean;
  connected: boolean;
  status: GoogleCalendarConnectionState;
  scope: string;
  owner_timezone: string;
}
