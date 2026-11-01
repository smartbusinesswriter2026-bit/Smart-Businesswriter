async () => {
  const out = {};
  try {
    const res = await cloudflare.request({
      method: "GET",
      path: `/accounts/${accountId}/r2/buckets`,
    });
    out.buckets = { success: res.success, status: res.status, result: res.result, errors: res.errors };
  } catch (error) {
    out.buckets_error = String(error);
  }
  try {
    const res2 = await cloudflare.request({
      method: "GET",
      path: `/accounts/${accountId}/r2/buckets/smart-business-writer-corpus`,
    });
    out.bucket = { success: res2.success, status: res2.status, result: res2.result, errors: res2.errors };
  } catch (error2) {
    out.bucket_error = String(error2);
  }
  return out;
}
