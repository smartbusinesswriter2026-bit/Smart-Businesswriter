// Route away and back, so the RENDERERS.home rebuild runs, then check the hero.
(async () => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  location.hash = "#/subject/finance";
  await wait(1200);
  location.hash = "#/home";
  await wait(1200);
  const hero = document.querySelector("#panel-home .hero") || document.querySelector(".hero");
  return {
    taglinePresentInDom: document.body.innerText.includes("BUSINESS | ACCOUNTING"),
    taglineElements: document.querySelectorAll(".tagline").length,
    heroChildren: hero ? [...hero.children].map((el) => el.tagName + "." + el.className) : null,
    sloganText: document.querySelector(".hero .slogan")?.innerText || null,
  };
})();
