import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import pluginQuery from '@tanstack/eslint-plugin-query'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  ...pluginQuery.configs['flat/recommended'],
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
      parserOptions: {
        ecmaVersion: 'latest',
        ecmaFeatures: { jsx: true },
        sourceType: 'module',
      },
    },
    rules: {
      // No jsx-uses-vars rule here, so JSX-only identifiers look "unused".
      // Capitalized names (all components) are ignored; `m` is the framer-motion
      // LazyMotion component used app-wide as <m.div> etc. (replaced `motion`).
      'no-unused-vars': ['error', {
        varsIgnorePattern: '^([A-Z_]|m$)',
        argsIgnorePattern: '^([A-Z_]|m$)',
      }],
    },
  },
])
