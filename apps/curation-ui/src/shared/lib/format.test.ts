import { describe, expect, it } from 'vitest';

import { confidenceBand, formatMoney, timeAgo } from './format';

describe('confidenceBand', () => {
  it('bands at the ADR-0004 thresholds', () => {
    expect(confidenceBand(0.9)).toBe('high');
    expect(confidenceBand(0.85)).toBe('high');
    expect(confidenceBand(0.7)).toBe('medium');
    expect(confidenceBand(0.65)).toBe('medium');
    expect(confidenceBand(0.5)).toBe('low');
  });
});

describe('formatMoney', () => {
  it('renders a decimal-string amount with the currency', () => {
    const rendered = formatMoney('1234.5', 'UAH');
    expect(rendered).toContain('UAH');
    // uk-UA groups thousands with a (non-breaking) space; \s matches it.
    expect(rendered).toMatch(/1\s?234/);
  });

  it('shows an em dash for a null amount', () => {
    expect(formatMoney(null, 'UAH')).toBe('—');
  });
});

describe('timeAgo', () => {
  it('reports fresh timestamps as just now', () => {
    const now = Date.parse('2026-07-13T12:00:00Z');
    expect(timeAgo('2026-07-13T11:59:30Z', now)).toBe('щойно');
  });

  it('reports hours for older timestamps', () => {
    const now = Date.parse('2026-07-13T12:00:00Z');
    expect(timeAgo('2026-07-13T09:00:00Z', now)).toBe('3 год тому');
  });
});
