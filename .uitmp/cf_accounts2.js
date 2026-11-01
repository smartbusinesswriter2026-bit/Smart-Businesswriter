async () => {
  const res = await cloudflare.request({ method: "GET", path: "/accounts" });
  return { success: res.success, status: res.status, result: res.result, errors: res.errors };
}
