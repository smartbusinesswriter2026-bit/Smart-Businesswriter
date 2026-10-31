(function () {
  return {
    docScrollW: document.documentElement.scrollWidth,
    docClientW: document.documentElement.clientWidth,
    bodyScrollW: document.body.scrollWidth,
    horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    railOpen: document.body.classList.contains("rail-open"),
    railW: Math.round(document.querySelector(".rail").getBoundingClientRect().width),
    toggleSvgW: Math.round(document.querySelector(".railtoggle .rt-expand").getBoundingClientRect().width),
    groupLabelText: document.querySelector(".railgroup-label").textContent,
    groupLabelOpacity: getComputedStyle(document.querySelector(".railgroup-label")).opacity,
    groupLabelX: Math.round(document.querySelector(".railgroup-label").getBoundingClientRect().x),
    groupLabelTextX: (function () {
      var el = document.querySelector(".railgroup-label");
      var r = document.createRange(); r.selectNodeContents(el);
      return Math.round(r.getBoundingClientRect().x);
    })(),
    firstLabelX: (function () {
      var el = document.querySelector("#railsubjects .railitem .railtext");
      var r = document.createRange(); r.selectNodeContents(el);
      return Math.round(r.getBoundingClientRect().x);
    })(),
    labels: Array.prototype.map.call(document.querySelectorAll("#railsubjects .railitem .railtext"), function (el) {
      return el.textContent;
    }),
    railItems: Array.prototype.map.call(document.querySelectorAll(".railitem"), function (a) {
      return a.getAttribute("href");
    })
  };
})()
