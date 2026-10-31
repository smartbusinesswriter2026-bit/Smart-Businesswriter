// Is the tagline gone from the rendered Home hero, and is the slogan still there?
(() => {
  const hero = document.querySelector("#panel-home .hero") || document.querySelector(".hero");
  const text = hero ? hero.innerText : null;
  const slogan = document.querySelector(".hero .slogan");
  return {
    heroText: text,
    taglinePresentInDom: document.body.innerText.includes("BUSINESS | ACCOUNTING"),
    taglineElements: document.querySelectorAll(".tagline").length,
    sloganPresent: !!slogan,
    sloganText: slogan ? slogan.innerText : null,
    heroChildren: hero ? [...hero.children].map((el) => el.tagName + "." + el.className) : null,
  };
})();
