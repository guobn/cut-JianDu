import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    user: null,
    session: null
  }),
  actions: {
    setSession(session) {
      this.session = session
      this.user = session?.user ?? null
    },
    logout() {
      this.user = null
      this.session = null
    }
  }
})
