/* Classify connected Routing Flow cards for their highlight color. */
(() => {
  function resolveNodeModes(graph) {
    const modes = new Map();
    const filtersById = new Map((graph?.filters || []).map(filter => [filter.id, filter]));
    const setMode = (kind, id, mode) => {
      if (id === null || id === undefined || id === "") return;
      const key = `${kind}:${id}`;
      const previous = modes.get(key);
      modes.set(key, previous && previous !== mode ? "mixed" : previous || mode);
    };

    for (const link of graph?.links || []) {
      const filters = (link.filter_ids || []).map(id => filtersById.get(id)).filter(Boolean);
      if (link.direct || filters.length === 0) {
        setMode("route", link.route_id, "single");
        setMode("destination", link.destination_id, "single");
      }
      for (const filter of filters) {
        setMode("route", link.route_id, "dual");
        setMode("filter", filter.id, "dual");
        setMode("destination", link.destination_id, "dual");
      }
    }

    return [...modes].map(([key, mode]) => {
      const separator = key.indexOf(":");
      return { kind: key.slice(0, separator), id: key.slice(separator + 1), mode };
    });
  }

  window.NowlertRoutingPulseModel = Object.freeze({ resolveNodeModes });
})();
