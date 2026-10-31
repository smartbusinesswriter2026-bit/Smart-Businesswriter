(function () {
  var r = function (el) {
    if (!el) return null;
    var b = el.getBoundingClientRect();
    var cs = getComputedStyle(el);
    return {
      text: (el.textContent || "").trim().slice(0, 40),
      x: Math.round(b.x), y: Math.round(b.y),
      w: Math.round(b.width), h: Math.round(b.height),
      opacity: cs.opacity, paddingLeft: cs.paddingLeft, display: cs.display,
      fontSize: cs.fontSize, color: cs.color, fontWeight: cs.fontWeight
    };
  };
  var out = {
    viewport: window.innerWidth + "x" + window.innerHeight,
    bodyClass: document.body.className,
    rail: r(document.querySelector(".rail")),
    toggle: r(document.querySelector(".railtoggle")),
    toggleSvg: r(document.querySelector(".railtoggle .rt-expand")),
    home: r(document.querySelector('.railitem[data-panel="home"]')),
    homeIcon: r(document.querySelector('.railitem[data-panel="home"] .ic')),
    homeText: r(document.querySelector('.railitem[data-panel="home"] .railtext')),
    groupLabel: r(document.querySelector(".railgroup-label")),
    firstSubject: r(document.querySelector('#railsubjects .railitem')),
    firstSubjectText: r(document.querySelector('#railsubjects .railitem .railtext')),
    calculator: r(document.querySelector('.railitem[data-panel="calculator"]')),
    check: r(document.querySelector('.railitem[data-panel="check"]')),
    rootVars: {
      railW: getComputedStyle(document.documentElement).getPropertyValue("--rail-w"),
      iconCol: getComputedStyle(document.documentElement).getPropertyValue("--icon-col")
    }
  };
  return out;
})()
