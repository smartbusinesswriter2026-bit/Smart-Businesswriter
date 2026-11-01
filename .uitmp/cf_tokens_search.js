async () => {
  const out = [];
  for (const [path, methods] of Object.entries(spec.paths)) {
    if (!/token/i.test(path)) continue;
    if (!/user|account_id/.test(path)) continue;
    for (const [method, op] of Object.entries(methods)) {
      out.push({
        method: method.toUpperCase(),
        path: path,
        summary: op?.summary,
        token_groups: op?.["x-api-token-group"] || null,
      });
    }
  }
  return out;
}
