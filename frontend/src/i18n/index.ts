import { createI18n } from 'vue-i18n'
import zhCN from './locales/zh-CN'
import en from './locales/en'
import ja from './locales/ja'
import ko from './locales/ko'

const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem('lang') || 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages: { 'zh-CN': zhCN, en, ja, ko },
})

export default i18n

/** 切换语言并持久化 */
export function setLocale(lang: string) {
  ;(i18n.global.locale as any).value = lang
  localStorage.setItem('lang', lang)
}
