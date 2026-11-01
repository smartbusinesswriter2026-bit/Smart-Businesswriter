async () => {
  const out = [];
  for (const [path, methods] of Object.entries(spec.paths)) {
    if (!/subscription|purchase|entitle/i.test(path)) continue;
    for (const [method, op] of Object.entries(methods)) {
      out.push({ method: method.toUpperCase(), path: path, summary: op?.summary, tags: op?.tags });
    }
  }
  return out;
}
