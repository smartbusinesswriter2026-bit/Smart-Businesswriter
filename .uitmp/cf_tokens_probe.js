async () => {
  const out = {};
  const account = "127515e9310b9d256df686b85a889907";
  const probes = [
    ["account_tokens", `/accounts/${account}/tokens`],
    ["account_token_groups", `/accounts/${account}/tokens/permission_groups`],
    ["r2_buckets", `/accounts/${account}/r2/buckets`],
    ["r2_subscription", `/accounts/${account}/r2/subscription`],
    ["r2_temp_creds", `/accounts/${account}/r2/temp-access-credentials`],
    ["zones", "/zones"],
  ];
  for (const [name, path] of probes) {
    try {
      const res = await cloudflare.request({ method: "GET", path: path });
      out[name] = { success: res.success, status: res.status, result: res.result, errors: res.errors };
    } catch (error) {
      out[name] = { error: String(error) };
    }
  }
  return out;
}
