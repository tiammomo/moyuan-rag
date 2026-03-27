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
  skill_version: string;
  priority: number;
  status: string;
  binding_config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface SkillDetail extends SkillListItem {
  manifest: Record<string, unknown>;
  readme_content?: string;
  prompts: SkillPromptFile[];
  bound_robots: SkillBinding[];
}

export interface SkillInstallResponse {
  message: string;
  skill: SkillDetail;
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
