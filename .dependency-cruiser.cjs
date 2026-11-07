/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: 'no-circular',
      severity: 'error',
      comment: 'Circular dependencies break tree-shaking and cause runtime undefined — fix via dependency inversion',
      from: {},
      to: { circular: true },
    },
    {
      name: 'no-orphans-frontend',
      severity: 'warn',
      comment: 'Orphan module in frontend/src — likely dead code or missing barrel export',
      from: { orphan: true, path: '^frontend/src', pathNot: ['\\.test\\.','__mocks__'] },
      to: {},
    },
    {
      // backend: api must not be imported by services (one-way: api -> services)
      name: 'backend-services-should-not-depend-on-api',
      severity: 'error',
      comment: 'services/ must not import from api/ — api is the composition root (api -> services one-way)',
      from: { path: '^backend/app/services' },
      to: { path: '^backend/app/api' },
    },
    {
      // frontend: features should not cross-import each other directly; use lib/ or store
      name: 'frontend-features-isolation',
      severity: 'warn',
      comment: 'features/* should not directly import sibling features — extract shared logic to lib/ or use store',
      from: { path: '^frontend/src/features/([^/]+)' },
      to: { path: '^frontend/src/features/([^/]+)', pathNot: '^frontend/src/features/$1' },
    },
    {
      name: 'no-non-package-json-deps',
      severity: 'error',
      comment: 'All npm deps must be in package.json',
      from: {},
      to: { dependencyTypes: ['npm-no-pkg','npm-unknown'] },
    },
  ],
  options: {
    doNotFollow: { path: 'node_modules' },
    tsPreCompilationDeps: false,
    tsConfig: { fileName: 'frontend/tsconfig.json' },
    enhancedResolveOptions: { exportsFields: ['exports'], conditionNames: ['import','require','node','default'] },
    reporterOptions: { archi: { collapsePattern: '^(frontend/src|backend/app)/[^/]+' } },
  },
};
