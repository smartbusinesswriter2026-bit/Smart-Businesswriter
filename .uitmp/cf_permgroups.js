async () => {
  const out = {};
  try {
    const res = await cloudflare.request({ method: "GET", path: "/user/tokens/permission_groups" });
    const groups = res.result && res.result.result ? res.result.result : res.result;
    const list = Array.isArray(groups) ? groups : (groups && groups.result) || [];
    out.r2_groups = (Array.isArray(list) ? list : [])
      .filter((g) => /r2|storage/i.test(JSON.stringify(g)))
      .map((g) => ({ id: g.id, name: g.name, scopes: g.scopes, meta: g.meta }));
    out.group_count = Array.isArray(list) ? list.length : null;
    out.sample = Array.isArray(list) ? list.slice(0, 3) : null;
  } catch (error) {
    out.permission_groups_error = String(error);
  }
  try {
    const res2 = await cloudflare.request({ method: "GET", path: "/user/tokens" });
    out.existing_tokens = res2.result;
  } catch (error2) {
    out.list_tokens_error = String(error2);
  }
  return out;
}
