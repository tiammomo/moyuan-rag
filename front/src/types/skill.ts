export interface SkillListItem {
  slug: string;
  name: string;
  version: string;
  description?: string;
  category?: string;
  source_type: string;
  status: string;
  install_path: string;
  installed_at?: string;
  readme_available: boolean;
  bound_robot_count: number;
}

export interface SkillListResponse {
  total: number;
  items: SkillListItem[];
}

export interface SkillPromptFile {
  key: string;
  path: string;
  content: string;
}

export interface SkillBinding {
  robot_id: number;
  robot_name?: string;
  skill_slug: string;
  skill_name?: string;
  skill_version: string;
  category?: string;
  skill_description?: string;
  priority: number;
  status: string;
  prompt_keys: string[];
  binding_config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface SkillDetail extends SkillListItem {
  manifest: Record<string, unknown>;
  readme_content?: string;
  prompts: SkillPromptFile[];
  bound_robots: SkillBinding[];
  installed_variants: SkillInstalledVariant[];
}

export interface SkillInstallResponse {
  message: string;
  skill: SkillDetail;
  install_task_id?: number;
}

export interface SkillBindingCreate {
  priority?: number;
  status?: string;
  binding_config?: Record<string, unknown>;
}

export interface SkillBindingUpdate {
  priority?: number;
  status?: string;
  binding_config?: Record<string, unknown>;
}

export interface SkillInstalledVariant {
  version: string;
  install_path: string;
  manifest_path: string;
  readme_available: boolean;
  is_current: boolean;
  installed_at?: string;
  prompt_keys: string[];
  bound_robot_count: number;
  bound_robot_ids: number[];
}

export interface SkillInstallTask {
  id: number;
  source_type: string;
  package_name?: string;
  package_url?: string;
  package_checksum?: string;
  package_signature?: string;
  signature_algorithm?: string;
  requested_by_user_id?: number;
  requested_by_username?: string;
  status: string;
  installed_skill_slug?: string;
  installed_skill_version?: string;
  error_message?: string;
  details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  finished_at?: string;
}

export interface SkillInstallTaskListResponse {
  total: number;
  items: SkillInstallTask[];
}

export interface SkillInstallTaskActionResponse {
  message: string;
  task: SkillInstallTask;
}

export interface SkillAuditLog {
  id: number;
  action: string;
  target_type: string;
  status: string;
  actor_user_id?: number;
  actor_username?: string;
  actor_role?: string;
  robot_id?: number;
  skill_slug?: string;
  skill_version?: string;
  install_task_id?: number;
  message?: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface SkillAuditLogListResponse {
  total: number;
  items: SkillAuditLog[];
}
