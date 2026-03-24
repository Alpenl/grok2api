(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = factory();
    return;
  }
  root.TokenFilters = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  function hasTag(token, tag) {
    return !!(token && Array.isArray(token.tags) && token.tags.includes(tag));
  }

  function isExpiredLike(token) {
    return !!token && token.status !== 'active' && token.status !== 'cooling';
  }

  function hasUpstreamRefusalToken(token) {
    if (!token) return false;
    if (hasTag(token, 'upstream_refused')) return true;
    return typeof token.last_fail_reason === 'string'
      && token.last_fail_reason.startsWith('upstream_refusal:');
  }

  function matchesTokenFilter(token, filter) {
    if (!token || !filter || filter === 'all') return true;
    if (filter === 'active') return token.status === 'active';
    if (filter === 'cooling') return token.status === 'cooling';
    if (filter === 'expired') return isExpiredLike(token);
    if (filter === 'nsfw') return hasTag(token, 'nsfw');
    if (filter === 'no-nsfw') return !hasTag(token, 'nsfw');
    if (filter === 'refused') return hasUpstreamRefusalToken(token);
    return true;
  }

  function buildTokenTabCounts(tokens) {
    var items = Array.isArray(tokens) ? tokens : [];
    return {
      all: items.length,
      active: items.filter(function (token) { return matchesTokenFilter(token, 'active'); }).length,
      cooling: items.filter(function (token) { return matchesTokenFilter(token, 'cooling'); }).length,
      expired: items.filter(function (token) { return matchesTokenFilter(token, 'expired'); }).length,
      nsfw: items.filter(function (token) { return matchesTokenFilter(token, 'nsfw'); }).length,
      'no-nsfw': items.filter(function (token) { return matchesTokenFilter(token, 'no-nsfw'); }).length,
      refused: items.filter(function (token) { return matchesTokenFilter(token, 'refused'); }).length,
    };
  }

  return {
    hasUpstreamRefusalToken: hasUpstreamRefusalToken,
    matchesTokenFilter: matchesTokenFilter,
    buildTokenTabCounts: buildTokenTabCounts,
  };
});
