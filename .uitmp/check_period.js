// Read the Home hero's lead and proof exactly as the page shows them.
(async () => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const read = () => {
    const lead = document.querySelector(".hero .slogan-lead");
    const proof = document.querySelector(".hero .slogan-proof");
    return {
      leadText: lead ? lead.textContent : null,
      leadEndsWithPeriod: lead ? lead.textContent.trim().endsWith(".") : null,
      proofText: proof ? proof.textContent : null,
    };
  };
  const first = read();
  location.hash = "#/subject/finance";
  await wait(1200);
  location.hash = "#/home";
  await wait(1200);
  const after = read();
  return { firstPaint: first, afterReRender: after };
})();
