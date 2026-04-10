import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo } from '@/types/user'

export const useUserStore = defineStore(
  'user',
  () => {
    const token = ref<string>('')
    const refreshToken = ref<string>('')
    const userInfo = ref<UserInfo | null>(null)

    const isLoggedIn = computed(() => !!token.value)

    const permissions = computed<string[]>(() => userInfo.value?.permissions ?? [])
    const roles = computed<string[]>(() => userInfo.value?.roles ?? [])

    function setToken(access: string, refresh: string) {
      token.value = access
      refreshToken.value = refresh
    }

    function setUserInfo(info: UserInfo) {
      userInfo.value = info
    }

    function clear() {
      token.value = ''
      refreshToken.value = ''
      userInfo.value = null
    }

    /** Check if the user has a specific permission code */
    function hasPermission(permissionCode: string): boolean {
      return permissions.value.includes(permissionCode)
    }

    /** Check if the user has any of the given permission codes */
    function hasAnyPermission(permissionCodes: string[]): boolean {
      return permissionCodes.some((code) => permissions.value.includes(code))
    }

    /** Check if the user has all of the given permission codes */
    function hasAllPermissions(permissionCodes: string[]): boolean {
      return permissionCodes.every((code) => permissions.value.includes(code))
    }

    /** Check if the user has a specific role */
    function hasRole(role: string): boolean {
      return roles.value.includes(role)
    }

    return {
      token,
      refreshToken,
      userInfo,
      isLoggedIn,
      permissions,
      roles,
      setToken,
      setUserInfo,
      clear,
      hasPermission,
      hasAnyPermission,
      hasAllPermissions,
      hasRole,
    }
  },
  {
    persist: {
      key: 'nesom-user',
      paths: ['token', 'refreshToken', 'userInfo'],
    },
  },
)
