export type DocumentStatus = "indexed" | "failed" | "missing";

export interface KnowledgeDocument {
  id: string;
  source_path: string;
  file_name: string;
  file_extension: string;
  mime_type: string;
  file_size: number;
  status: DocumentStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  indexed_at: string | null;
}

export interface KnowledgeDocumentList {
  items: KnowledgeDocument[];
  page: number;
  page_size: number;
  total: number;
}

export interface KnowledgeScanResult {
  discovered: number;
  indexed: number;
  unchanged: number;
  unsupported: number;
  failed: number;
}

export interface KnowledgeSearchResult {
  document_id: string;
  file_name: string;
  source_path: string;
  source_locator: string;
  excerpt: string;
  relevance_score: number | null;
}

export interface KnowledgeSearchResponse {
  query: string;
  items: KnowledgeSearchResult[];
}
