async () => {
  const op = spec.paths["/accounts/{account_id}/subscriptions"]?.post;
  const list = spec.paths["/accounts/{account_id}/subscriptions"]?.get;
  return {
    post_summary: op?.summary,
    post_body: op?.requestBody,
    post_params: op?.parameters,
    get_summary: list?.summary,
    get_params: list?.parameters,
  };
}
