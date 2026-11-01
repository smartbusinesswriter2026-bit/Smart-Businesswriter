async () => {
  const accounts = await cloudflare.request({ method: "GET", path: "/accounts" });
  const zones = await cloudflare.request({ method: "GET", path: "/zones", query: { per_page: 20 } });
  return {
    accounts: accounts.result,
    accounts_info: accounts.result_info || null,
    zones: zones.success ? zones.result : { error: zones.errors },
  };
}
