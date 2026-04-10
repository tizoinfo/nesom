/** System configuration module types */

export type ConfigType = 'STRING' | 'NUMBER' | 'BOOLEAN' | 'JSON'

export interface SysConfig {
  id: number
  config_key: string
  config_value: string | null
  config_type: ConfigType
  module: string
  description: string | null
  is_sensitive: number
  is_system: number
  created_time: string
  updated_time: string | null
}

export interface SysDict {
  id: number
  dict_type: string
  dict_code: string
  dict_name: string
  dict_value: string | null
  sort_order: number
  parent_id: number | null
  is_system: number
  status: number
  remark: string | null
  created_time: string
}

export interface HealthStatus {
  status: string
  components: {
    database: string
    redis: string
    minio: string
  }
  details: {
    configCount: number
    dictCount: number
    lastRefreshTime: string
  }
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}
