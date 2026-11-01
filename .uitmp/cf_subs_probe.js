async () => {
  const out = {};
  const account = "127515e9310b9d256df686b85a889907";
  const probes = [
    ["subscriptions", `/accounts/${account}/subscriptions`],
    ["entitlements", `/accounts/${account}/entitlements`],
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
