(function () {
  var item = document.querySelector('#railsubjects .railitem');
  var tip = item.querySelector('.railtip');
  var rail = document.querySelector('.rail');
  item.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
  var tb = tip.getBoundingClientRect();
  var rb = rail.getBoundingClientRect();
  var cs = getComputedStyle(tip);
  return {
    tipText: tip.textContent.slice(0, 60),
    tip: { x: Math.round(tb.x), y: Math.round(tb.y), w: Math.round(tb.width), h: Math.round(tb.height), opacity: cs.opacity, display: cs.display },
    rail: { x: Math.round(rb.x), w: Math.round(rb.width), overflow: getComputedStyle(rail).overflow },
    visibleWidthOutsideRail: Math.round(Math.max(0, tb.right - rb.right)),
    tipLeftBeyondRail: Math.round(tb.x - rb.right)
  };
})()
