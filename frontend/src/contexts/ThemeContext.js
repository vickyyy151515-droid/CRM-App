import { createContext, useContext, useState, useEffect } from 'react';

const ThemeContext = createContext();

// Role-based theme configurations
export const ROLE_THEMES = {
  master_admin: {
    name: 'Master Admin',
    primary: 'amber',
    accent: 'yellow',
    // Tailwind class mappings
    bgGradient: 'from-amber-500 to-yellow-500',
    bgGradientHover: 'from-amber-600 to-yellow-600',
    bgSolid: 'bg-amber-500',
    bgSolidHover: 'hover:bg-amber-600',
    bgLight: 'bg-amber-50 dark:bg-amber-900/20',
    bgMuted: 'bg-amber-100 dark:bg-amber-900/30',
    text: 'text-amber-600 dark:text-amber-400',
    textLight: 'text-amber-500',
    border: 'border-amber-200 dark:border-amber-800',
    ring: 'ring-amber-500',
    focusRing: 'focus:ring-amber-500',
    activeNav: 'bg-gradient-to-r from-amber-500 to-yellow-500 text-white',
    badge: 'bg-amber-100 dark:bg-amber-900/50 text-amber-800 dark:text-amber-300',
    icon: 'text-amber-500',
    headerAccent: 'border-b-2 border-amber-500',
    avatarBg: 'bg-gradient-to-br from-amber-400 to-yellow-500',
    buttonPrimary: 'bg-amber-600 hover:bg-amber-700 text-white',
    buttonSecondary: 'bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 hover:bg-amber-100 dark:hover:bg-amber-900/50',
  },
  admin: {
    name: 'Admin',
    primary: 'indigo',
    accent: 'purple',
    bgGradient: 'from-indigo-500 to-purple-600',
    bgGradientHover: 'from-indigo-600 to-purple-700',
    bgSolid: 'bg-indigo-500',
    bgSolidHover: 'hover:bg-indigo-600',
    bgLight: 'bg-indigo-50 dark:bg-indigo-900/20',
    bgMuted: 'bg-indigo-100 dark:bg-indigo-900/30',
    text: 'text-indigo-600 dark:text-indigo-400',
    textLight: 'text-indigo-500',
    border: 'border-indigo-200 dark:border-indigo-800',
    ring: 'ring-indigo-500',
    focusRing: 'focus:ring-indigo-500',
    activeNav: 'bg-slate-900 dark:bg-indigo-600 text-white',
    badge: 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-800 dark:text-indigo-300',
    icon: 'text-indigo-500',
    headerAccent: 'border-b-2 border-indigo-500',
    avatarBg: 'bg-indigo-500',
    buttonPrimary: 'bg-indigo-600 hover:bg-indigo-700 text-white',
    buttonSecondary: 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/50',
  },
  staff: {
    name: 'Staff',
    primary: 'blue',
    accent: 'cyan',
    bgGradient: 'from-blue-500 to-cyan-500',
    bgGradientHover: 'from-blue-600 to-cyan-600',
    bgSolid: 'bg-blue-500',
    bgSolidHover: 'hover:bg-blue-600',
    bgLight: 'bg-blue-50 dark:bg-blue-900/20',
    bgMuted: 'bg-blue-100 dark:bg-blue-900/30',
    text: 'text-blue-600 dark:text-blue-400',
    textLight: 'text-blue-500',
    border: 'border-blue-200 dark:border-blue-800',
    ring: 'ring-blue-500',
    focusRing: 'focus:ring-blue-500',
    activeNav: 'bg-blue-600 text-white',
    badge: 'bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300',
    icon: 'text-blue-500',
    headerAccent: 'border-b-2 border-blue-500',
    avatarBg: 'bg-blue-500',
    buttonPrimary: 'bg-blue-600 hover:bg-blue-700 text-white',
    buttonSecondary: 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/50',
  }
};

export function ThemeProvider({ children }) {
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('theme');
    if (saved) {
      return saved === 'dark';
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  const [userRole, setUserRole] = useState('admin');

  useEffect(() => {
    const root = document.documentElement;
    if (darkMode) {
      root.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      root.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [darkMode]);

  const toggleTheme = () => {
    setDarkMode(prev => !prev);
  };

  // Get theme based on role
  const getRoleTheme = (role) => {
    return ROLE_THEMES[role] || ROLE_THEMES.staff;
  };

  const roleTheme = getRoleTheme(userRole);

  return (
    <ThemeContext.Provider value={{ 
      darkMode, 
      toggleTheme, 
      userRole, 
      setUserRole, 
      roleTheme,
      getRoleTheme,
      ROLE_THEMES 
    }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
