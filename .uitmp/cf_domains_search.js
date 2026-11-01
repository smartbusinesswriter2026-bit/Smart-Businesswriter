async () => {
  const out = [];
  for (const [path, methods] of Object.entries(spec.paths)) {
    if (!/domains/i.test(path)) continue;
    for (const [method, op] of Object.entries(methods)) {
      out.push({
        method: method.toUpperCase(),
        path: path,
        summary: op?.summary,
        body: op?.requestBody ? JSON.stringify(op.requestBody).slice(0, 600) : null,
      });
    }
  }
  return out;
}
