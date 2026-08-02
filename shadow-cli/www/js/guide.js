/* ── Onboarding System ──────────────────────────────────── */
let obState = { step: 1, rawSkills: [], generatedConfigs: [], presetName: null };

function showOnboard(show){
  document.getElementById('onboard-overlay').classList.toggle('hidden', !show);
}

async function checkOnboarding(){
  try {
    const r = await apiGet('/onboard/status');
    if(r.onboarded){ showOnboard(false); loadDashboard(); }
    else {
      showOnboard(true); showOnboardStep(1); await loadPresets();
    }
  } catch(e){ showOnboard(false); loadDashboard(); }
}

async function loadPresets(){
  try {
    const r = await apiGet('/onboard/presets');
    const grid = document.getElementById('preset-grid');
    grid.innerHTML = (r.presets||[]).map(p =>
      `<div class="preset-card" onclick="obSelectPreset('${p.id}')">
        <div class="pname">${p.name}</div><div class="pdesc">${p.description}</div></div>`
    ).join('');
  } catch(e){}
}

function obSelectPreset(id){ obState.presetName = id; obState.rawSkills = []; obNext(); }
function obAddSkill(){
  const input = document.getElementById('ob-skill-input');
  const val = input.value.trim();
  if(!val || obState.rawSkills.includes(val)) return;
  obState.rawSkills.push(val); input.value = ''; renderObTags();
}
function obRemoveSkill(i){ obState.rawSkills.splice(i, 1); renderObTags(); }
function renderObTags(){
  const el = document.getElementById('ob-skill-tags');
  el.innerHTML = obState.rawSkills.map((s,i) =>
    `<div class="skill-tag">${s} <span class="remove" onclick="obRemoveSkill(${i})">×</span></div>`
  ).join('');
}

function showOnboardStep(n){
  obState.step = n;
  document.getElementById('ob-step1').style.display = n===1 ? '' : 'none';
  document.getElementById('ob-step2').style.display = n===2 ? '' : 'none';
  document.getElementById('ob-step3').style.display = n===3 ? '' : 'none';
  document.getElementById('ob-prev').style.display = n>1 ? '' : 'none';
  document.getElementById('ob-next').style.display = n<3 ? '' : 'none';
  for(let i=1;i<=3;i++){
    const el = document.getElementById('os-'+i);
    el.className = 'onboard-step';
    if(i<n) el.classList.add('done');
    if(i===n) el.classList.add('active');
  }
}

async function obNext(){
  if(obState.step === 1){
    if(!obState.presetName && obState.rawSkills.length === 0){
      alert('请选择一个预设套餐或至少添加一个自定义技能'); return;
    }
    showOnboardStep(2);
    document.getElementById('ob-config-loading').style.display = '';
    document.getElementById('ob-config-list').innerHTML = '';
    try {
      let body = obState.presetName ? { preset: obState.presetName } : { descriptions: obState.rawSkills };
      const r = await apiPost('/onboard/configure', body);
      obState.generatedConfigs = r.configs || [];
      obState.presetName = r.preset_name || obState.presetName;
    } catch(e){
      obState.generatedConfigs = [];
      document.getElementById('ob-config-loading').innerHTML =
        '<span style="color:var(--red)">⚠️ 加载失败: ' + e.message + '</span>';
    }
    renderObConfigs();
    document.getElementById('ob-config-loading').style.display = obState.generatedConfigs.length > 0 ? 'none' : '';
  } else if(obState.step === 2){
    const configs = getEditedConfigs();
    try {
      const r = await apiPost('/onboard/save', { skills: configs, template_used: obState.presetName });
      if(r.success){
        document.getElementById('ob-complete-msg').textContent =
          `已配置 ${configs.length} 项技能，开始你的成长之旅吧！`;
        showOnboardStep(3);
      }
    } catch(e){}
  }
}

function obPrev(){ if(obState.step > 1) showOnboardStep(obState.step - 1); }
function obFinish(){ showOnboard(false); loadDashboard(); showGuide(); }
function obSkip(){
  try { apiPost('/onboard/save', { skills: [], template_used: 'skipped' }); } catch(e){}
  showOnboard(false); loadDashboard(); showGuide();
}

function renderObConfigs(){
  const list = document.getElementById('ob-config-list');
  list.innerHTML = obState.generatedConfigs.map((c, i) =>
    `<div class="config-item" data-idx="${i}">
      <div class="c-icon">${c.icon||'⭐'}</div>
      <div><div class="c-name">${c.name||c.id}</div>
      <div class="c-detail">${c.category||'其他'} · 每${c.unit||'次'}+${c.exp_per_unit||0} EXP · 上限${c.daily_cap||0} · 目标${c.daily_target||0}</div></div>
      <button class="c-remove" onclick="obRemoveConfig(${i})">移除</button></div>`
  ).join('');
}
function obRemoveConfig(i){ obState.generatedConfigs.splice(i, 1); renderObConfigs(); }
function getEditedConfigs(){
  return obState.generatedConfigs.map(c => ({
    id: c.id, name: c.name, category: c.category, unit: c.unit, icon: c.icon,
    exp_formula: c.exp_formula || 'linear', exp_per_unit: c.exp_per_unit,
    daily_cap: c.daily_cap, daily_target: c.daily_target,
  }));
}

/* ── Guide System ───────────────────────────────────────── */
const GUIDE_STORAGE = 'shadow_guide_done';
const guideSteps = [
  { icon:'⚔️', title:'欢迎来到暗影世界', text:'这里是你成长的战场。每次练习、每次学习、每次坚持，都会化为力量。', target:null },
  { icon:'⚡', title:'快捷操作 — 你的武器库', text:'点击这里记录你的练习，获得 EXP。技能按钮会根据你的配置动态生成。', target:'#tab-actions' },
  { icon:'📋', title:'每日任务 — 你的目标', text:'每天更新的任务列表，完成所有任务可领取额外奖励和连击加成。', target:'#tab-tasks' },
  { icon:'📊', title:'状态面板 — 你的成长', text:'查看你的等级、经验、属性和战力。升级后记得分配属性点！', target:'#tab-dashboard' },
  { icon:'📜', title:'手册 — 你的地图', text:'侧边栏的 📜 手册随时可用，查阅玩法说明、经验公式和快速入门。', target:'#tab-manual' },
];
let guideCurrent = 0;

function showGuide(){
  if(localStorage.getItem(GUIDE_STORAGE)) return;
  guideCurrent = 0; renderGuideStep();
  document.getElementById('guide-overlay').classList.add('show');
}
function hideGuide(){
  document.getElementById('guide-overlay').classList.remove('show');
  document.getElementById('guide-target').style.display = 'none';
  document.getElementById('guide-tooltip').style.display = 'none';
}
function skipGuide(){
  localStorage.setItem(GUIDE_STORAGE, 'true'); hideGuide();
  toast('暗影手册在侧边栏随时可用 📜', 'info');
}

function guideNext(){
  if(guideCurrent >= guideSteps.length - 1){
    localStorage.setItem(GUIDE_STORAGE, 'true'); hideGuide();
    loadDashboard(); navToTab('dashboard');
    showNarration('⚔️ 暗影启程', '你的冒险开始了。记住，每次记录都是向着暗影君主迈出的一步。',
      '随时查看 📜 手册了解完整玩法', 5);
    return;
  }
  guideCurrent++; renderGuideStep();
}

function renderGuideStep(){
  const step = guideSteps[guideCurrent];
  const dots = document.getElementById('guide-dots');
  const icon = document.getElementById('guide-icon');
  const title = document.getElementById('guide-title');
  const text = document.getElementById('guide-text');
  const target = document.getElementById('guide-target');
  const tooltip = document.getElementById('guide-tooltip');
  const actions = document.getElementById('guide-overlay').querySelector('.g-actions');

  dots.innerHTML = guideSteps.map((_, i) => {
    let cls = 'g-dot';
    if(i < guideCurrent) cls += ' done';
    else if(i === guideCurrent) cls += ' active';
    return `<div class="${cls}"></div>`;
  }).join('');

  icon.textContent = step.icon; title.textContent = step.title; text.textContent = step.text;
  if(guideCurrent === guideSteps.length - 1)
    actions.innerHTML = '<button class="btn btn-primary" onclick="guideNext()">开始冒险</button>';
  else
    actions.innerHTML = '<button class="btn btn-primary" onclick="guideNext()">下一步</button>';

  if(step.target){
    const tabMatch = step.target.match(/#tab-(\w+)/);
    if(tabMatch) navToTab(tabMatch[1]);
    setTimeout(() => {
      const el = document.querySelector(step.target);
      if(!el){ target.style.display = 'none'; tooltip.style.display = 'none'; return; }
      const rect = el.getBoundingClientRect();
      target.style.display = 'block';
      target.style.top = (rect.top - 4) + 'px';
      target.style.left = (rect.left - 4) + 'px';
      target.style.width = (rect.width + 8) + 'px';
      target.style.height = (rect.height + 8) + 'px';
      tooltip.style.display = 'block';
      tooltip.style.top = Math.min(rect.bottom + 12, window.innerHeight - 100) + 'px';
      tooltip.style.left = Math.min(rect.left, window.innerWidth - 300) + 'px';
      tooltip.querySelector('#gt-title').textContent = step.title;
      tooltip.querySelector('#gt-text').textContent = step.text;
    }, 400);
  } else {
    target.style.display = 'none'; tooltip.style.display = 'none';
  }
}
