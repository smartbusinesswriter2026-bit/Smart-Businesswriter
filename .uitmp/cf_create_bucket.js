async () => {
  const created = await cloudflare.request({
    method: "POST",
    path: `/accounts/${accountId}/r2/buckets`,
    body: { name: "smart-business-writer-corpus" },
  });
  const list = await cloudflare.request({ method: "GET", path: `/accounts/${accountId}/r2/buckets` });
  const dev = await cloudflare.request({
    method: "GET",
    path: `/accounts/${accountId}/r2/buckets/smart-business-writer-corpus/domains/managed`,
  });
  const custom = await cloudflare.request({
    method: "GET",
    path: `/accounts/${accountId}/r2/buckets/smart-business-writer-corpus/domains/custom`,
  });
  return {
    create: { success: created.success, status: created.status, result: created.result, errors: created.errors },
    buckets: list.success ? list.result : list.errors,
    r2dev: { success: dev.success, status: dev.status, result: dev.result, errors: dev.errors },
    custom_domains: { success: custom.success, status: custom.status, result: custom.result, errors: custom.errors },
  };
}
