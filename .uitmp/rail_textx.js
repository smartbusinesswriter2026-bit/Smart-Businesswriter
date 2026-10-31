// Where does the label column start, and where does the green strip end?
(() => {
  const rail = document.getElementById("rail");
  const accent = rail.querySelector(".railaccent");
  const txt = rail.querySelector(".railitem .railtext");
  const label = rail.querySelector(".railgroup-label");
  const glyph = rail.querySelector(".railitem .ic svg");
  const toggle = document.getElementById("railtoggle");
  const chev = [...toggle.querySelectorAll("svg")].find((s) => getComputedStyle(s).display !== "none");
  const sep = rail.querySelector(".railsep");
  const r = (el) => {
    if (!el) return null;
    const b = el.getBoundingClientRect();
    return { x: +b.left.toFixed(2), right: +b.right.toFixed(2), w: +b.width.toFixed(2) };
  };
  return {
    open: document.body.classList.contains("rail-open"),
    rail: r(rail),
    accent: r(accent),
    glyph: r(glyph),
    label: r(txt),
    groupLabel: r(label),
    chevron: r(chev),
    sep: r(sep),
    window: { w: window.innerWidth, h: window.innerHeight },
  };
})();
