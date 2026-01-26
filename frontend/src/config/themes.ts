export interface Theme {
  name: string
  displayName: string
  primary: string
  primaryHover: string
  secondary: string
  accent: string
  background: string
  surface: string
  text: string
  textMuted: string
  border: string
  success: string
  danger: string
  warning: string
  info: string
  gradient: string
  gradientSecondary: string
}

export const themes: Record<string, Theme> = {
  default: {
    name: 'default',
    displayName: '默认蓝',
    primary: '#667eea',
    primaryHover: '#5a67d8',
    secondary: '#764ba2',
    accent: '#f093fb',
    background: '#f7fafc',
    surface: '#ffffff',
    text: '#2d3748',
    textMuted: '#718096',
    border: '#e2e8f0',
    success: '#48bb78',
    danger: '#f56565',
    warning: '#ed8936',
    info: '#4299e1',
    gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    gradientSecondary: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  },
  ocean: {
    name: 'ocean',
    displayName: '海洋蓝',
    primary: '#0ea5e9',
    primaryHover: '#0284c7',
    secondary: '#0284c7',
    accent: '#00d4ff',
    background: '#f0f9ff',
    surface: '#ffffff',
    text: '#1e293b',
    textMuted: '#64748b',
    border: '#cbd5e1',
    success: '#10b981',
    danger: '#ef4444',
    warning: '#f59e0b',
    info: '#0ea5e9',
    gradient: 'linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%)',
    gradientSecondary: 'linear-gradient(135deg, #00d4ff 0%, #0ea5e9 100%)',
  },
  forest: {
    name: 'forest',
    displayName: '森林绿',
    primary: '#10b981',
    primaryHover: '#059669',
    secondary: '#059669',
    accent: '#34d399',
    background: '#ecfdf5',
    surface: '#ffffff',
    text: '#1e293b',
    textMuted: '#64748b',
    border: '#d1fae5',
    success: '#10b981',
    danger: '#ef4444',
    warning: '#f59e0b',
    info: '#0ea5e9',
    gradient: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    gradientSecondary: 'linear-gradient(135deg, #34d399 0%, #10b981 100%)',
  },
  sunset: {
    name: 'sunset',
    displayName: '日落橙',
    primary: '#f97316',
    primaryHover: '#ea580c',
    secondary: '#ea580c',
    accent: '#fb923c',
    background: '#fff7ed',
    surface: '#ffffff',
    text: '#1e293b',
    textMuted: '#64748b',
    border: '#fed7aa',
    success: '#10b981',
    danger: '#ef4444',
    warning: '#f97316',
    info: '#0ea5e9',
    gradient: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
    gradientSecondary: 'linear-gradient(135deg, #fb923c 0%, #f97316 100%)',
  },
  purple: {
    name: 'purple',
    displayName: '皇家紫',
    primary: '#8b5cf6',
    primaryHover: '#7c3aed',
    secondary: '#7c3aed',
    accent: '#c084fc',
    background: '#faf5ff',
    surface: '#ffffff',
    text: '#1e293b',
    textMuted: '#64748b',
    border: '#e9d5ff',
    success: '#10b981',
    danger: '#ef4444',
    warning: '#f59e0b',
    info: '#0ea5e9',
    gradient: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
    gradientSecondary: 'linear-gradient(135deg, #c084fc 0%, #8b5cf6 100%)',
  },
  dark: {
    name: 'dark',
    displayName: '暗夜黑',
    primary: '#6366f1',
    primaryHover: '#4f46e5',
    secondary: '#4f46e5',
    accent: '#818cf8',
    background: '#1f2937',
    surface: '#374151',
    text: '#f9fafb',
    textMuted: '#9ca3af',
    border: '#4b5563',
    success: '#10b981',
    danger: '#ef4444',
    warning: '#f59e0b',
    info: '#3b82f6',
    gradient: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
    gradientSecondary: 'linear-gradient(135deg, #818cf8 0%, #6366f1 100%)',
  },
  rose: {
    name: 'rose',
    displayName: '玫瑰红',
    primary: '#e11d48',
    primaryHover: '#be123c',
    secondary: '#be123c',
    accent: '#fb7185',
    background: '#fff1f2',
    surface: '#ffffff',
    text: '#1e293b',
    textMuted: '#64748b',
    border: '#fecdd3',
    success: '#10b981',
    danger: '#e11d48',
    warning: '#f59e0b',
    info: '#0ea5e9',
    gradient: 'linear-gradient(135deg, #e11d48 0%, #be123c 100%)',
    gradientSecondary: 'linear-gradient(135deg, #fb7185 0%, #e11d48 100%)',
  },
}

export const defaultTheme = 'default'

export function getTheme(name: string): Theme {
  return themes[name] || themes.default
}
