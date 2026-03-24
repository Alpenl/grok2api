const test = require('node:test');
const assert = require('node:assert/strict');

const {
  hasUpstreamRefusalToken,
  getUpstreamRefusalReasonCode,
  formatFailureReasonCode,
  matchesTokenFilter,
  buildTokenTabCounts,
} = require('../_public/static/admin/js/token-filters.js');

test('hasUpstreamRefusalToken detects refusal by tag', () => {
  assert.equal(
    hasUpstreamRefusalToken({
      tags: ['nsfw', 'upstream_refused'],
      last_fail_reason: null,
    }),
    true,
  );
});

test('hasUpstreamRefusalToken detects refusal by normalized reason', () => {
  assert.equal(
    hasUpstreamRefusalToken({
      tags: [],
      last_fail_reason: 'upstream_refusal:generic_refusal',
    }),
    true,
  );
});

test('matchesTokenFilter returns only refused tokens for refused filter', () => {
  const refused = {
    status: 'active',
    tags: ['upstream_refused'],
    last_fail_reason: 'upstream_refusal:generic_refusal',
  };
  const normal = {
    status: 'active',
    tags: ['nsfw'],
    last_fail_reason: null,
  };

  assert.equal(matchesTokenFilter(refused, 'refused'), true);
  assert.equal(matchesTokenFilter(normal, 'refused'), false);
});

test('getUpstreamRefusalReasonCode extracts refusal code suffix', () => {
  assert.equal(
    getUpstreamRefusalReasonCode({
      tags: ['upstream_refused'],
      last_fail_reason: 'upstream_refusal:generic_refusal',
    }),
    'generic_refusal',
  );
});

test('formatFailureReasonCode humanizes structured reason codes', () => {
  assert.equal(formatFailureReasonCode('generic_refusal'), 'generic refusal');
  assert.equal(formatFailureReasonCode('policy-blocked'), 'policy blocked');
});

test('buildTokenTabCounts includes refused count without breaking existing counts', () => {
  const counts = buildTokenTabCounts([
    {
      status: 'active',
      tags: ['nsfw', 'upstream_refused'],
      last_fail_reason: 'upstream_refusal:generic_refusal',
    },
    {
      status: 'cooling',
      tags: [],
      last_fail_reason: null,
    },
    {
      status: 'expired',
      tags: [],
      last_fail_reason: 'auth_failed',
    },
  ]);

  assert.deepEqual(counts, {
    all: 3,
    active: 1,
    cooling: 1,
    expired: 1,
    nsfw: 1,
    'no-nsfw': 2,
    refused: 1,
  });
});
