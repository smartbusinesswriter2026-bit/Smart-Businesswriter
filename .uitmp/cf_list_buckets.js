async () => {
  const res = await cloudflare.request({
    method: "GET",
    path: `/accounts/127515e9310b9d256df686b85a889907/r2/buckets`,
  });
  return { success: res.success, status: res.status, result: res.result, errors: res.errors };
}
