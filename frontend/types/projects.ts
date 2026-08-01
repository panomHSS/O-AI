export type ProjectStatus = "ACTIVE" | "PAUSED" | "COMPLETED" | "ARCHIVED";

export interface Project {
  id: string;
  title: string;
  objective: string;
  status: ProjectStatus;
  current_summary: string | null;
  next_action: string | null;
  current_revision: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectRevision {
  id: string;
  revision_number: number;
  title: string;
  objective: string;
  status: ProjectStatus;
  current_summary: string | null;
  next_action: string | null;
  change_note: string;
  created_at: string;
}

export interface ProjectListResponse {
  items: Project[];
  page: number;
  page_size: number;
  total: number;
}

export interface ProjectHistoryResponse {
  items: ProjectRevision[];
}

export interface CreateProjectRequest {
  title: string;
  objective: string;
  change_note: string;
}

export interface UpdateProjectDetailsRequest {
  expected_revision: number;
  change_note: string;
  title?: string;
  objective?: string;
}

export interface RecordProjectProgressRequest {
  expected_revision: number;
  change_note: string;
  current_summary: string | null;
}

export interface ChangeNextActionRequest {
  expected_revision: number;
  change_note: string;
  next_action: string | null;
}

export interface ChangeProjectStatusRequest {
  expected_revision: number;
  change_note: string;
  status: ProjectStatus;
}
