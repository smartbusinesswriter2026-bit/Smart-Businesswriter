// Measure the collapsed rail: strip box, icon box, glyph box, clip box.
(() => {
  const rail = document.getElementById("rail");
  const subj = document.getElementById("railsubjects");
  const css = (el, p) => {
    const r = el.getBoundingClientRect();
    return {
      x: +r.left.toFixed(2), right: +r.right.toFixed(2),
      w: +r.width.toFixed(2), h: +r.height.toFixed(2),
    };
  };
  const out = {
    open: document.body.classList.contains("rail-open"),
    rail: css(rail),
    railPad: getComputedStyle(rail).padding,
    vars: {
      railW: getComputedStyle(document.documentElement).getPropertyValue("--rail-w").trim(),
      railPad: getComputedStyle(document.documentElement).getPropertyValue("--rail-pad").trim(),
      railIcW: getComputedStyle(document.documentElement).getPropertyValue("--rail-ic-w").trim(),
      railIcPad: getComputedStyle(document.documentElement).getPropertyValue("--rail-ic-pad").trim(),
      railTextX: getComputedStyle(document.documentElement).getPropertyValue("--rail-text-x").trim(),
    },
    toggle: (() => {
      const t = document.getElementById("railtoggle");
      const svg = t.querySelector("svg:not([style*='display: none'])") || t.querySelector("svg");
      const vis = [...t.querySelectorAll("svg")].find((s) => getComputedStyle(s).display !== "none");
      return { box: css(t), glyph: vis ? css(vis) : null, transform: getComputedStyle(t).transform };
    })(),
    items: [],
  };
  const clip = subj ? subj.getBoundingClientRect() : null;
  document.querySelectorAll(".railitem").forEach((it) => {
    const ic = it.querySelector(".ic");
    const svg = ic && ic.querySelector("svg");
    const txt = it.querySelector(".railtext");
    const parent = it.parentElement;
    const pclip = parent.getBoundingClientRect();
    const ov = getComputedStyle(parent);
    const o = {
      label: txt ? txt.textContent.trim() : it.getAttribute("href"),
      item: css(it),
      ic: ic ? css(ic) : null,
      glyph: svg ? css(svg) : null,
      parentOverflowX: ov.overflowX,
      parentBox: { x: +pclip.left.toFixed(2), right: +pclip.right.toFixed(2) },
      clippedRight: svg ? +(svg.getBoundingClientRect().right - pclip.right).toFixed(2) : null,
      clippedLeft: svg ? +(pclip.left - svg.getBoundingClientRect().left).toFixed(2) : null,
    };
    out.items.push(o);
  });
  return out;
})();
