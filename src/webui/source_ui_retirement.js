"use strict";

(() => {
  delete VIEW_TITLES.sources;

  const sourcesNav = document.querySelector('#primary-nav [data-view="sources"]');
  if (sourcesNav) sourcesNav.remove();

  const previousNavigate = navigate;
  navigate = function sourceRetirementNavigate(view, historyMode = "push") {
    if (view === "sources") view = "destinations";
    return previousNavigate(view, historyMode);
  };

  if (state.currentView === "sources") navigate("destinations", "replace");
})();
