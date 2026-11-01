async () => {
  const out = {};
  const account = "127515e9310b9d256df686b85a889907";
  const bucket = "smart-business-writer-corpus";

  try {
    const list = await cloudflare.request({ method: "GET", path: `/accounts/${account}/r2/buckets` });
    const buckets = (list.result && list.result.buckets) || list.result || [];
    out.existing_buckets = (Array.isArray(buckets) ? buckets : []).map((b) => ({
      name: b.name, created_on: b.created_on, location: b.location, storage_class: b.storage_class,
    }));
  } catch (error) {
    out.list_error = String(error);
  }

  try {
    const created = await cloudflare.request({
      method: "POST",
      path: `/accounts/${account}/r2/buckets`,
      body: { name: bucket },
    });
    out.create = { success: created.success, status: created.status, result: created.result, errors: created.errors };
  } catch (error) {
    out.create_error = String(error);
  }

  try {
    const dev = await cloudflare.request({
      method: "GET",
      path: `/accounts/${account}/r2/buckets/${bucket}/domains/managed`,
    });
    out.r2dev = { success: dev.success, status: dev.status, result: dev.result, errors: dev.errors };
  } catch (error) {
    out.r2dev_error = String(error);
  }

  try {
    const details = await cloudflare.request({
      method: "GET",
      path: `/accounts/${account}/r2/buckets/${bucket}`,
    });
    out.bucket = { success: details.success, status: details.status, result: details.result, errors: details.errors };
  } catch (error) {
    out.bucket_error = String(error);
  }

  return out;
}
