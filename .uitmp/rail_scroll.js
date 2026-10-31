// Does the subject list's scrollbar eat the icon column?
(() => {
  const subj = document.getElementById("railsubjects");
  const rail = document.getElementById("rail");
  const rcs = getComputedStyle(rail);
  const first = subj.querySelector(".railitem .ic svg");
  const g = first.getBoundingClientRect();
  const left = subj.getBoundingClientRect().left;
  return {
    railWidth: rcs.width,
    railPadding: rcs.padding,
    railContentRight: rail.getBoundingClientRect().right - 1 - parseFloat(rcs.paddingRight),
    listOffsetW: subj.offsetWidth,
    listClientW: subj.clientWidth,
    scrollbarPx: subj.offsetWidth - subj.clientWidth,
    scrolls: subj.scrollHeight > subj.clientHeight,
    scrollportRight: left + subj.clientWidth,
    glyphLeft: +g.left.toFixed(2),
    glyphRight: +g.right.toFixed(2),
    glyphW: +g.width.toFixed(2),
    glyphFullyVisible: g.right <= left + subj.clientWidth,
  };
})();
