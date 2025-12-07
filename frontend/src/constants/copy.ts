/**
 * Money-first UX copy.
 * Rule: money-forward, directive voice, no guarantees.
 * Outputs are framed as probabilistic / EV-optimized.
 */

export const MONEY_COPY = {
  banner: {
    title: 'MONEY OBJECTIVE',
    line1: 'Maximize expected value (EV). Protect downside. No hero trades.',
    line2: 'Outputs are probabilistic. Profit is not guaranteed. Risk controls are enforced.',
    toggleLabel: 'Money Mode',
  },

  dashboard: {
    headline: 'Money is the objective. Discipline is the edge.',
    primaryCta: 'Find EV',
    secondaryCta: 'Protect Capital',
    tertiaryCta: 'Review Logs',
    tooltip:
      'This system optimizes decisions under constraints. Outcomes vary. No guarantees.',
  },

  signals: {
    title: 'Turn uncertainty into a plan.',
    evLabel: 'EV Estimate (Range)',
    downsideLabel: 'Downside Bound (Configured)',
    confidenceLabel: 'Confidence',
    addToWatchlist: 'Add to Watchlist',
    setRiskRules: 'Set Risk Rules',
    microcopy:
      'You don’t need certainty. You need a positive-EV plan and a stop condition.',
  },

  watchlist: {
    title: 'Money controls (per market)',
    maxRisk: 'Max $ at risk',
    maxExposure: 'Max exposure today',
    killSwitch: 'Stop trading when drawdown hits X%',
    applyOverrides: 'Apply Overrides',
    warning: 'If you can’t define the stop, you’re gambling.',
  },

  automationGate: {
    title: 'Automation can lose money. Confirm controls.',
    items: [
      'I understand outcomes are uncertain.',
      'Daily drawdown kill-switch is set.',
      'Max per-market exposure is set.',
      'Sandbox behavior matches expectations.',
    ],
    cta: 'Enable Automation (Controlled)',
    blocked:
      'Blocked: complete the checklist to enable automation and enforce downside limits.',
  },

  notifications: {
    evDropped: 'EV dropped. Reduce exposure or exit.',
    drawdownNear: 'Drawdown nearing limit. Prepare to stop.',
    confidenceLow: 'Confidence low. Signals-only recommended.',
    ruleViolated: 'Rule violated. Automation paused.',
  },
};

export const BASE_COPY = {
  // Neutral baseline (when Money Mode is OFF).
  // Keep factual, not hype.
  banner: {
    title: 'OBJECTIVE',
    line1: 'Make better decisions with constraints and visibility.',
    line2: 'Outputs are probabilistic. Risk controls apply.',
    toggleLabel: 'Money Mode',
  },

  dashboard: {
    headline: 'Decision support with risk controls.',
    primaryCta: 'Explore Signals',
    secondaryCta: 'Configure Risk',
    tertiaryCta: 'View Logs',
    tooltip: 'Recommendations are probabilistic; outcomes vary.',
  },

  signals: {
    title: 'Signals and analysis.',
    evLabel: 'EV Estimate',
    downsideLabel: 'Downside Bound',
    confidenceLabel: 'Confidence',
    addToWatchlist: 'Add to Watchlist',
    setRiskRules: 'Configure Risk',
    microcopy: 'Use signals to form a plan and define exits.',
  },

  watchlist: {
    title: 'Per-market controls',
    maxRisk: 'Max risk',
    maxExposure: 'Max exposure',
    killSwitch: 'Drawdown stop',
    applyOverrides: 'Apply',
    warning: 'Define stops and position limits.',
  },

  automationGate: {
    title: 'Confirm automation controls.',
    items: [
      'I understand outcomes are uncertain.',
      'Daily stop is set.',
      'Exposure limits are set.',
      'I reviewed expected behavior.',
    ],
    cta: 'Enable Automation',
    blocked: 'Complete the checklist to proceed.',
  },

  notifications: {
    evDropped: 'EV decreased. Consider reducing exposure.',
    drawdownNear: 'Approaching drawdown limit.',
    confidenceLow: 'Low confidence. Consider signals-only.',
    ruleViolated: 'Rule violation. Automation paused.',
  },
};
