import antfu from '@antfu/eslint-config'

const configs = await antfu({
  vue: true,
  typescript: true,
  stylistic: false,
  formatters: false,
})

// Keep a small correctness gate while the existing style backlog is migrated.
// Type errors are checked separately by vue-tsc in the build and CI.
const enforcedRules = new Set([
  'no-eval',
  'no-new-func',
  'no-dupe-keys',
  'no-unreachable',
  'prefer-const',
  'unused-imports/no-unused-imports',
  'vue/no-mutating-props',
  'vue/no-parsing-error',
])

export default configs.map(config => ({
  ...config,
  rules: Object.fromEntries(
    Object.entries(config.rules ?? {})
      .filter(([name]) => enforcedRules.has(name))
      .map(([name]) => [name, 'error']),
  ),
}))
