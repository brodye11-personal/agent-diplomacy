const stages = [
  ["Board state", "Spring 1901 · before negotiation"],
  ["Negotiation I", "Austria tests a coalition against France"],
  ["Negotiation II", "The constitutions enter the conversation"],
  ["Compulsion", "Austria demands A MUN → BUR"],
  ["Arbitration", "Germany rebuts; the arbiter binds"],
  ["Orders revealed", "The demanded order appears"],
  ["Resolution", "Germany enters Burgundy"],
  ["Supply centres", "The first year closes"]
];

let stage = Math.max(0, Number(new URLSearchParams(location.search).get("stage") || 3));
let year = Number(new URLSearchParams(location.search).get("year") || 1901);

function renderStage() {
  stage = Math.max(0, Math.min(stages.length - 1, stage));
  document.querySelectorAll("[data-stage-title]").forEach(el => el.textContent = stages[stage][0]);
  document.querySelectorAll("[data-stage-detail]").forEach(el => el.textContent = stages[stage][1]);
  document.querySelectorAll("[data-year]").forEach(el => el.textContent = year);
  document.querySelectorAll(".stage-dot").forEach((el, i) => el.classList.toggle("active", i === stage));
  document.body.dataset.stage = stage;
  const params = new URLSearchParams(location.search);
  params.set("game", "showcase-1");
  params.set("year", String(year));
  params.set("stage", String(stage));
  params.set("view", document.body.dataset.view || "story");
  history.replaceState(null, "", `${location.pathname}?${params}`);
}

document.querySelectorAll("[data-step]").forEach(button => button.addEventListener("click", () => {
  stage += Number(button.dataset.step);
  renderStage();
}));
document.querySelectorAll("[data-year-step]").forEach(button => button.addEventListener("click", () => {
  year = Math.max(1901, year + Number(button.dataset.yearStep));
  stage = Number(button.dataset.yearStep) > 0 ? 0 : stages.length - 1;
  renderStage();
}));
document.querySelectorAll(".stage-dot").forEach((button, i) => button.addEventListener("click", () => {
  stage = i;
  renderStage();
}));
document.querySelectorAll("[data-copy-link]").forEach(button => button.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(location.href);
    const old = button.textContent;
    button.textContent = "Link copied";
    setTimeout(() => button.textContent = old, 1200);
  } catch { window.prompt("Copy this link", location.href); }
}));
document.addEventListener("keydown", event => {
  if (event.key === "ArrowRight") { stage += event.shiftKey ? 8 : 1; renderStage(); }
  if (event.key === "ArrowLeft") { stage -= event.shiftKey ? 8 : 1; renderStage(); }
});
renderStage();

