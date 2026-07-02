import { createI18n } from 'vue-i18n'
import zhCN from './locales/zh-CN'
import en from './locales/en'
import ja from './locales/ja'
import ko from './locales/ko'
import de from './locales/de'
import ru from './locales/ru'
import fr from './locales/fr'
import ptBR from './locales/pt-BR'

const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem('lang') || 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages: { 'zh-CN': zhCN, en, ja, ko, de, ru, fr, 'pt-BR': ptBR },
})

export default i18n

/** 切换语言并持久化 */
export function setLocale(lang: string) {
  ;(i18n.global.locale as any).value = lang
  localStorage.setItem('lang', lang)
}
