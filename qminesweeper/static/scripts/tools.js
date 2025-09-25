// static/scripts/tools.js

const singleQ = new Set(['X','Y','Z','H','S','SDG','SX','SXDG','SY','SYDG']);
const twoQ    = new Set(['CX','CY','CZ','SWAP']);
const allTools = new Set(['M','P', ...singleQ, ...twoQ]);

let currentTool = localStorage.getItem("qms_tool") || "M";
let firstPick = null;

function setTool(t) {
  currentTool = t;
  localStorage.setItem("qms_tool", t);
  firstPick = null; 
  
  // active style
  document.querySelectorAll('.btn.tool').forEach(b => {
    b.classList.toggle('active', b.textContent === t);
  });
  document.querySelectorAll('.board button').forEach(b => b.classList.remove('pick'));
}

function sendCmd(cmd) {
  document.getElementById("cmd-input").value = cmd;
  document.getElementById("move-form").submit();
}

function clickCell(r, c) {
  const rc = `${r+1},${c+1}`;
  if (currentTool === 'M') { sendCmd(rc); return; }
  if (currentTool === 'P') { sendCmd(`P ${rc}`); return; }
  if (singleQ.has(currentTool)) { sendCmd(`${currentTool} ${rc}`); return; }
  if (twoQ.has(currentTool)) {
    if (!firstPick) {
      firstPick = [r,c];
      // highlight the first pick
      const row = document.querySelectorAll('.board tr')[r];
      const btn = row.querySelectorAll('button')[c];
      btn.classList.add('pick');
      return;
    } else {
      const [r1,c1] = firstPick;
      firstPick = null;
      // clear highlight from all buttons
      document.querySelectorAll('.board button').forEach(b => b.classList.remove('pick'));
      const rc1 = `${r1+1},${c1+1}`;
      sendCmd(`${currentTool} ${rc1} ${rc}`);
    }
  }
}

// restore last selected tool on load
document.addEventListener("DOMContentLoaded", () => {
  setTool(currentTool);
});

// keyboard shortcuts
document.addEventListener("keydown", (event) => {
  let key = event.key.toUpperCase();

  if (key === "C") {
    document.addEventListener("keydown", function secondKey(ev) {
      const combo = "C" + ev.key.toUpperCase();
      if (allTools.has(combo)) {
        setTool(combo);
      }
    }, { once: true });
    return;
  }

  if (allTools.has(key)) {
    setTool(key);
  }
});
