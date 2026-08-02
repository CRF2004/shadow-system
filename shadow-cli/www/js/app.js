/* ── Toast ──────────────────────────────────────────────── */
function toast(msg, type='info'){
  const el = document.createElement('div');
  el.className = 'toast ' + type;
  el.textContent = msg;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

/* ── Tab navigation ─────────────────────────────────────── */
document.querySelectorAll('#nav a').forEach(a => {
  a.addEventListener('click', () => {
    document.querySelectorAll('#nav a').forEach(x => x.classList.remove('active'));
    a.classList.add('active');
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.getElementById('tab-' + a.dataset.tab).classList.add('active');
    // Load tab data
    const tab = a.dataset.tab;
    if(tab==='dashboard') loadDashboard();
    else if(tab==='tasks') loadTasks();
    else if(tab==='actions') loadActions();
    else if(tab==='achievements') loadAchievements();
    else if(tab==='shop') loadShop();
    else if(tab==='army') loadArmy();
    else if(tab==='dungeons') loadDungeons();
    else if(tab==='bosses') loadBosses();
    else if(tab==='integrations') loadIntegrations();
    else if(tab==='guild') loadGuild();
    else if(tab==='analytics') loadAnalytics();
  });
});

function navToTab(tabId){
  // Update sidebar nav active state
  document.querySelectorAll('#nav a').forEach(a => {
    a.classList.toggle('active', a.dataset.tab === tabId);
  });
  // Show target tab, hide others
  document.querySelectorAll('.tab-content').forEach(t => {
    t.classList.toggle('active', t.id === 'tab-' + tabId);
  });
  // Load tab data
  if(tabId==='dashboard') loadDashboard();
  else if(tabId==='tasks') loadTasks();
  else if(tabId==='actions') loadActions();
  else if(tabId==='achievements') loadAchievements();
  else if(tabId==='shop') loadShop();
  else if(tabId==='army') loadArmy();
  else if(tabId==='dungeons') loadDungeons();
  else if(tabId==='bosses') loadBosses();
  else if(tabId==='integrations') loadIntegrations();
  else if(tabId==='guild') loadGuild();
  else if(tabId==='analytics') loadAnalytics();
}

function showAuthOverlay(show){
  const overlay = document.getElementById('auth-overlay');
  if(show) overlay.classList.remove('hidden');
  else overlay.classList.add('hidden');
}

function showLogin(){
  document.getElementById('auth-login').style.display='';
  document.getElementById('auth-register').style.display='none';
  document.getElementById('login-error').textContent='';
}
function showRegister(){
  document.getElementById('auth-login').style.display='none';
  document.getElementById('auth-register').style.display='';
  document.getElementById('reg-error').textContent='';
}

async function doLogin(){
  const user = document.getElementById('login-user').value.trim();
  const pass = document.getElementById('login-pass').value;
  if(!user||!pass){ document.getElementById('login-error').textContent='请填写用户名和密码'; return; }
  const r = await apiPostRaw('/auth/login', {username: user, password: pass});
  if(r.success && r.token){
    setToken(r.token);
    showAuthOverlay(false);
    toast('登录成功！', 'success');
    connectSSE();
    checkOnboarding();
    // Show guide for onboarded users who haven't seen it
    if(!localStorage.getItem(GUIDE_STORAGE)){
      setTimeout(() => {
        apiGet('/onboard/status').then(r => {
          if(r.onboarded) showGuide();
        }).catch(() => {});
      }, 1500);
    }
  } else {
    document.getElementById('login-error').textContent = r.message || '登录失败';
  }
}

async function doRegister(){
  const user = document.getElementById('reg-user').value.trim();
  const name = document.getElementById('reg-name').value.trim();
  const pass = document.getElementById('reg-pass').value;
  const pass2 = document.getElementById('reg-pass2').value;
  if(!user||!pass){ document.getElementById('reg-error').textContent='请填写用户名和密码'; return; }
  if(pass!==pass2){ document.getElementById('reg-error').textContent='两次密码不一致'; return; }
  const r = await apiPostRaw('/auth/register', {username: user, password: pass, displayName: name||user});
  if(r.success && r.token){
    setToken(r.token);
    showAuthOverlay(false);
    toast(r.message || '注册成功！', 'success');
    connectSSE();
    checkOnboarding();
  } else {
    document.getElementById('reg-error').textContent = r.message || '注册失败';
  }
}

function doLogout(){
  setToken('');
  showAuthOverlay(true);
  showLogin();
  toast('已退出登录', 'info');
}

/* ── Dynamic Record/Guild Select Population ────────────────── */
function skillOptionsHtml(s){
  // Generate <option> HTML from skillConfig (used inline in template strings)
  const skills = (s && s.skillConfig && s.skillConfig.skills) || [];
  if(skills.length > 0){
    return skills.map(sk =>
      `<option value="${sk.id}">${sk.icon||'⭐'} ${sk.name}</option>`
    ).join('');
  }
  // Fallback to hardcoded defaults
  return '<option value="commit">Commit 代码提交</option>'+
    '<option value="coding">Coding 编码</option>'+
    '<option value="vocabulary">Vocabulary 背单词</option>'+
    '<option value="exercise">Exercise 运动</option>'+
    '<option value="reading">Reading 阅读</option>';
}

function populateRecordTypeSelect(s){
  const sel = document.getElementById('rec-type');
  if(!sel) return;
  const skills = (s.skillConfig && s.skillConfig.skills) || [];
  if(skills.length > 0){
    sel.innerHTML = skills.map(sk =>
      `<option value="${sk.id}">${sk.icon||'⭐'} ${sk.name}</option>`
    ).join('');
  } else {
    // Fallback to hardcoded defaults
    sel.innerHTML =
      '<option value="commit">Commit 代码提交</option>'+
      '<option value="coding">Coding 编码</option>'+
      '<option value="vocabulary">Vocabulary 背单词</option>'+
      '<option value="exercise">Exercise 运动</option>'+
      '<option value="reading">Reading 阅读</option>';
  }
}

function populateGuildActionSelects(s){
  const skills = (s.skillConfig && s.skillConfig.skills) || [];
  const options = skills.length > 0
    ? skills.map(sk => `<option value="${sk.id}">${sk.icon||'⭐'} ${sk.name}</option>`).join('')
    : '<option value="commit">Commit</option><option value="coding">编码</option>'+
      '<option value="reading">阅读</option><option value="exercise">运动</option>'+
      '<option value="vocabulary">背单词</option>';
  // Update both guild action selects if they exist (they may not if guild section not rendered yet)
  const contribSel = document.getElementById('guild-contribute-type');
  const attackSel = document.getElementById('guild-attack-type');
  if(contribSel) contribSel.innerHTML = options;
  if(attackSel) attackSel.innerHTML = options;
}

/* ── Core Loop Visualizer ───────────────────────────────── */
function renderCoreLoop(s){
  const el = document.getElementById('core-loop');
  if(!el) return;

  const statPoints = s.statPoints || 0;
  const skills = (s.skillConfig && s.skillConfig.skills) || [];
  const hasSkills = skills.length > 0;

  // Determine player state for each step
  const todayTasks = s.totalExp > 0; // has any activity at all
  const hasExp = s.exp > 0 || s.level > 1;
  const hasStatPoints = statPoints > 0;
  const levelReached = s.level >= 1;
  const hasInventoryOrDungeon = s.achievementCount > 0 || s.inventoryCount > 0;

  // Step definitions
  const steps = [
    { id: 'record', icon: '⚡', label: '记录行为', hint: '获得 EXP', tab: 'actions', completed: false },
    { id: 'exp', icon: '📈', label: '获得 EXP', hint: `${s.expPct}% 升级`, tab: 'dashboard', completed: hasExp },
    { id: 'levelup', icon: '🎉', label: '升级', hint: `LV.${s.level}`, tab: 'dashboard', completed: s.level > 1 },
    { id: 'stats', icon: '📊', label: '分配属性', hint: hasStatPoints ? `${statPoints} 点可用` : '已满', tab: 'actions', completed: !hasStatPoints },
    { id: 'dungeon', icon: '🏰', label: '挑战副本', hint: levelReached ? '开始冒险' : '需 LV.1', tab: 'dungeons', completed: false },
  ];

  // Find recommended step (highest priority uncompleted step)
  let recommended = null;
  if(hasStatPoints) recommended = 'stats';
  else if(s.level > 1) recommended = 'dungeon';
  else recommended = 'record';

  let html = '<div class="cl-title"><span class="cl-icon">🔄</span> 核心循环 — <span id="cl-rec-label" class="text-gold" style="font-size:12px">下一步: ';
  if(recommended === 'stats') html += '分配属性点';
  else if(recommended === 'dungeon') html += '挑战副本';
  else html += '记录你的第一个行为';
  html += '</span></div>';

  html += '<div class="cl-steps">';
  steps.forEach((step, i) => {
    let cls = 'cl-step';
    if(step.completed) cls += ' completed';
    if(step.id === recommended) cls += ' recommended';

    html += `<div class="${cls}" onclick="navToTab('${step.tab}')" title="点击前往 ${step.label}">`;
    if(step.id === recommended) html += '<span class="cl-rec-badge">推荐</span>';
    if(step.completed) html += '<span class="cl-check">✓</span>';
    html += `<span class="cl-icon">${step.icon}</span>`;
    html += `<span class="cl-label">${step.label}</span>`;
    html += `<span class="cl-hint">${step.hint}</span>`;
    html += '</div>';

    // Arrow between steps (not after last)
    if(i < steps.length - 1) html += '<span class="cl-arrow">→</span>';
  });
  html += '</div>';

  el.innerHTML = html;
}

/* ── Dashboard ──────────────────────────────────────────── */
async function loadDashboard(){
  const s = await apiGet('/status');
  // Render core loop visualizer
  renderCoreLoop(s);
  // Populate record type select from player's skill config
  populateRecordTypeSelect(s);
  // Populate guild action selects from player's skill config
  populateGuildActionSelects(s);
  document.getElementById('header-ver').textContent = 'v' + s.version;
  document.getElementById('header-gold').textContent = s.gold;
  document.getElementById('header-gems').textContent = s.gems;
  document.getElementById('header-streak').textContent = s.streak;
  document.getElementById('alloc-points-info').textContent =
    s.statPoints > 0 ? `可用属性点: ${s.statPoints}` : '属性点: 已满 (0)';
  document.getElementById('alloc-points-info').className =
    s.statPoints > 0 ? 'text-gold mb-8' : 'mb-8';

  // Big stats
  const statsEl = document.getElementById('dash-stats');
  statsEl.innerHTML = `
    <div class="card stat-big"><div class="value">LV.${s.level}</div><div class="label">等级</div></div>
    <div class="card stat-big"><div class="value" style="color:var(--purple)">${s.title}</div><div class="label">称号</div></div>
    <div class="card stat-big"><div class="value">${s.power}</div><div class="label">战力</div></div>
    <div class="card stat-big"><div class="value">${s.gold}</div><div class="label">金币</div></div>
  `;

  // Bars
  const barsEl = document.getElementById('dash-bars');
  barsEl.innerHTML = `
    <div class="card-title">状态条</div>
    <div style="margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px">
        <span>HP</span><span>${s.hp}/100</span>
      </div>
      <div class="bar-wrap"><div class="bar-fill hp" style="width:${s.hp}%"></div></div>
    </div>
    <div style="margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px">
        <span>MP</span><span>${s.mp}/100</span>
      </div>
      <div class="bar-wrap"><div class="bar-fill mp" style="width:${s.mp}%"></div></div>
    </div>
    <div style="margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px">
        <span>EXP</span><span>${s.exp}/${s.expToNext} (${s.expPct}%)</span>
      </div>
      <div class="bar-wrap"><div class="bar-fill exp" style="width:${s.expPct}%"></div></div>
    </div>
  `;

  // Stats row
  const rowEl = document.getElementById('dash-stats-row');
  const stats = s.stats;
  const names = {strength:'力量 STR',agility:'敏捷 AGI',sense:'感知 SEN',vitality:'体力 VIT',intelligence:'智力 INT'};
  let html = '<div class="card"><h3>属性</h3>';
  if(s.statPoints > 0) html += `<div class="text-gold mb-8">可用属性点: ${s.statPoints}</div>`;
  for(const [k,v] of Object.entries(stats)){
    html += `<div class="stat-row">
      <span class="stat-label">${names[k]||k}</span>
      <span class="stat-value">${v}</span>
      <div class="bar-wrap stat-bar" style="height:8px"><div class="bar-fill exp" style="width:${Math.min(v*2,100)}%"></div></div>
    </div>`;
  }
  html += '</div>';

  html += '<div class="card"><h3>概览</h3>';
  const overview = [
    ['总EXP', s.totalExp], ['Commit数', s.commitCount],
    ['士兵', s.soldierCount], ['成就', `${s.achievementCount}/${s.achievementTotal}`],
    ['Boss击破', s.bossesDefeated], ['背包物品', s.inventoryCount],
    ['连击', s.streak + '天'], ['COMBO', s.combo],
  ];
  for(const [label,val] of overview){
    html += `<div class="stat-row"><span class="stat-label">${label}</span><span class="stat-value">${val}</span></div>`;
  }
  html += '</div>';
  rowEl.innerHTML = html;
}

/* ── Tasks ──────────────────────────────────────────────── */
async function loadTasks(){
  const d = await apiGet('/tasks');
  document.getElementById('task-date').textContent = d.date;
  const list = document.getElementById('task-list');
  if(!d.tasks.length){
    list.innerHTML = '<div class="empty">暂无任务</div>';
    return;
  }
  let html = '';
  let completed = 0;
  for(const t of d.tasks){
    const cls = t.status==='completed' ? 'completed' : '';
    if(t.status==='completed') completed++;
    const diffColor = {E:'#6b7280',D:'#2ed573',C:'#3742fa',B:'#a855f7',A:'#ff4757',S:'#ffd700'}[t.difficulty]||'#6b7280';
    html += `<div class="task-item ${cls}">
      <div class="check">${t.status==='completed'?'✓':''}</div>
      <div class="info">
        <div class="name">${t.name}</div>
        <div class="detail">${t.current}/${t.target}</div>
      </div>
      <span class="diff" style="color:${diffColor};border:1px solid ${diffColor}">${t.difficulty}</span>
      <span class="reward">+${t.reward} EXP</span>
    </div>`;
  }
  list.innerHTML = html;

  const total = d.tasks.length;
  const actions = document.getElementById('task-actions');
  if(completed === total && total > 0){
    actions.innerHTML = '<button class="btn btn-primary" onclick="doClaimDaily()">领取奖励</button>';
  } else {
    actions.innerHTML = `<span class="text-dim">进度: ${completed}/${total} | 总奖励: ${d.tasks.reduce((a,t)=>a+t.reward,0)} EXP</span>`;
  }
}

async function doClaimDaily(){
  const r = await apiPost('/claim-daily', {});
  if(r.messages){
    showNarration(
      '🏆 每日奖励',
      r.messages.filter(m => m.includes('升级')).join('\n') || r.messages[0] || '所有任务已完成！',
      r.messages.join(' | '),
      5
    );
  }
  if(r.achievements) r.achievements.forEach(a => toast(`成就: ${a.name}`, 'success'));
  loadTasks();
  loadDashboard();
}

/* ── Actions ────────────────────────────────────────────── */

/* Dynamic Skill Buttons */
let selectedSkill = null;

async function loadActions(){
  try {
    // Fetch skills directly
    const skData = await apiGet('/skills');
    const skills = skData.skills || [];
    // Fetch status for dropdown population
    const s = await apiGet('/status');
    const gridEl = document.getElementById('skill-quick-grid');
    const emptyEl = document.getElementById('empty-skills-msg');
    const legacyCard = document.getElementById('legacy-record-card');

    // Populate the select dropdown dynamically too
    populateRecordTypeSelect(s);
    populateGuildActionSelects(s);

    if(skills.length === 0){
      // No skills configured — show empty state
      gridEl.innerHTML = '';
      emptyEl.style.display = '';
      legacyCard.style.display = '';
      closeRecordPanel();
      return;
    }

    // Hide empty state, show skill grid
    emptyEl.style.display = 'none';
    legacyCard.style.display = '';
    gridEl.innerHTML = skills.map(sk => {
      const perUnit = sk.exp_per_unit || 0;
      const dailyCap = sk.daily_cap || 0;
      const dailyTarget = sk.daily_target || 0;
      const unit = sk.unit || '次';
      return `<div class="skill-btn" data-skill-id="${sk.id}" onclick="selectSkill('${sk.id}')">
        <span class="sk-icon">${sk.icon || '⭐'}</span>
        <span class="sk-name">${sk.name}</span>
        <span class="sk-cat">${sk.category || '其他'}</span>
        <span class="sk-exp">+${perUnit} EXP/${unit}</span>
        ${dailyCap > 0 ? `<span class="sk-target">上限 ${dailyCap} EXP | 目标 ${dailyTarget}${unit}</span>` : ''}
      </div>`;
    }).join('');

    // If previously selected skill is still valid, keep panel open
    if(selectedSkill && !skills.find(sk => sk.id === selectedSkill.id)){
      closeRecordPanel();
    }
  } catch(e){
    console.error('loadActions failed:', e);
  }
}

function selectSkill(skillId){
  // Fetch status to get skill details
  apiGet('/status').then(s => {
    const skills = (s.skillConfig && s.skillConfig.skills) || [];
    const skill = skills.find(sk => sk.id === skillId);
    if(!skill) return;

    selectedSkill = skill;

    // Highlight the selected button
    document.querySelectorAll('.skill-btn').forEach(btn => {
      btn.classList.toggle('selected', btn.dataset.skillId === skillId);
    });

    // Populate record panel
    const panel = document.getElementById('record-panel');
    document.getElementById('rp-icon').textContent = skill.icon || '⭐';
    document.getElementById('rp-name').textContent = skill.name;
    const unit = skill.unit || '次';
    document.getElementById('rp-unit').textContent = `单位: ${unit}`;
    document.getElementById('rp-exp-info').textContent =
      `每次 +${skill.exp_per_unit || 0} EXP | 每日上限 ${skill.daily_cap || 0} EXP | 目标 ${skill.daily_target || 0}${unit}`;
    document.getElementById('rp-unit-label').textContent = unit;

    // Set default quantity to daily target
    const defaultQty = skill.daily_target || 1;
    document.getElementById('rp-qty').value = defaultQty;

    // Hide previous result
    const resultEl = document.getElementById('rp-result');
    resultEl.className = 'rp-result';
    resultEl.textContent = '';

    // Show panel
    panel.classList.add('visible');

    // Scroll to panel
    panel.scrollIntoView({behavior: 'smooth', block: 'nearest'});
  }).catch(e => console.error('selectSkill failed:', e));
}

function setRpQty(n){
  const input = document.getElementById('rp-qty');
  const current = parseInt(input.value) || 0;
  input.value = current + n;
  input.focus();
}

function closeRecordPanel(){
  const panel = document.getElementById('record-panel');
  panel.classList.remove('visible');
  selectedSkill = null;
  document.querySelectorAll('.skill-btn').forEach(btn => btn.classList.remove('selected'));
}

async function doRecordFromPanel(){
  if(!selectedSkill) return;
  const qty = parseInt(document.getElementById('rp-qty').value) || 1;
  if(qty <= 0) { toast('数量必须大于 0', 'error'); return; }

  const resultEl = document.getElementById('rp-result');
  resultEl.className = 'rp-result show success';
  resultEl.textContent = '⏳ 记录中...';

  try {
    const r = await apiPost('/record', {type: selectedSkill.id, quantity: qty});
    if(r.success){
      // Show result in panel
      let msg = `✅ +${r.exp} EXP`;
      if(r.levelups && r.levelups.length > 0){
        msg += ` | 🎉 ${r.levelups.join(', ')}`;
      }
      resultEl.className = 'rp-result show success';
      resultEl.textContent = msg;

      // Show cinematic for levelup or normal record
      if(r.levelups && r.levelups.length > 0){
        const narTexts = getSkillNarrative(selectedSkill.id, 'levelup');
        const nar = pickRandom(narTexts);
        const unit = selectedSkill.unit || '次';
        showNarration(nar.t, nar.b, `${selectedSkill.icon||'⭐'} ${selectedSkill.name} — 等级提升 (+${r.exp} EXP)`, 5);
      } else {
        const narTexts = getSkillNarrative(selectedSkill.id, 'record');
        const nar = pickRandom(narTexts);
        const unit = selectedSkill.unit || '次';
        showNarration(`${selectedSkill.icon||'⭐'} ${selectedSkill.name}`, nar.b, `${nar.t} | +${r.exp} EXP | 完成 ${qty}${unit}`, 4);
      }

      if(r.achievements) r.achievements.forEach(a => toast(`成就: ${a.name}`, 'success'));
      if(r.bossesDefeated) r.bossesDefeated.forEach(b => toast(`Boss击破: ${b.name}`, 'error'));

      // Refresh dashboard status
      loadDashboard();

      // Update daily target progress if available
      if(r.taskProgress){
        // Could show progress indicator here
      }
    } else {
      resultEl.className = 'rp-result show error';
      resultEl.textContent = `❌ ${r.message}`;
      toast(r.message, 'error');
    }
  } catch(e){
    resultEl.className = 'rp-result show error';
    resultEl.textContent = `❌ 请求失败: ${e.message}`;
    toast('记录失败', 'error');
  }
}

/* ── Actions (legacy) ───────────────────────────────────── */
async function doRecord(){
  const type = document.getElementById('rec-type').value;
  const qty = parseInt(document.getElementById('rec-qty').value) || 1;
  const r = await apiPost('/record', {type, quantity: qty});
  if(r.success){
    // Get skill info for narrative (don't block if this fails)
    let skillName = type, skillIcon = '⭐', unit = '次', lvl = 1;
    try {
      const s = await apiGet('/status');
      lvl = s.level;
      const skills = (s.skillConfig && s.skillConfig.skills) || [];
      const skill = skills.find(sk => sk.id === type);
      if(skill){
        skillName = skill.name;
        skillIcon = skill.icon || '⭐';
        unit = skill.unit || '次';
      }
    } catch(e){}

    if(r.levelups && r.levelups.length > 0){
      // Level up: show cinematic narrative
      const narTexts = getSkillNarrative(type, 'levelup');
      const nar = pickRandom(narTexts);
      showNarration(nar.t, nar.b, `${skillIcon} ${skillName} — 等级提升至 ${lvl} (+${r.exp} EXP)`, 5);
    } else {
      // Normal record: show narrative
      const narTexts = getSkillNarrative(type, 'record');
      const nar = pickRandom(narTexts);
      showNarration(`${skillIcon} ${skillName}`, nar.b, `${nar.t} | +${r.exp} EXP | 完成 ${qty}${unit}练习`, 4);
    }

    if(r.achievements) r.achievements.forEach(a => toast(`成就: ${a.name}`, 'success'));
    if(r.bossesDefeated) r.bossesDefeated.forEach(b => toast(`Boss击破: ${b.name}`, 'error'));
    loadDashboard();
  } else {
    toast(r.message, 'error');
  }
}

async function doAllocate(){
  const stat = document.getElementById('alloc-stat').value;
  const amt = parseInt(document.getElementById('alloc-amt').value) || 1;
  const r = await apiPost('/allocate-stat', {stat, amount: amt});
  if(r.success){
    toast('属性分配成功！', 'success');
    loadDashboard();
  } else {
    toast(r.message, 'error');
  }
}

async function doSummon(){
  const type = document.getElementById('summon-type').value || null;
  const r = await apiPost('/summon', {type});
  if(r.success){
    if(r.obtained){
      showNarration(
        '⚔️ 暗影召唤',
        `${r.obtained.name} 响应了你的召唤，从暗影中现身`,
        `LV.${r.obtained.level} [${r.obtained.type}] — 你的军队又壮大了一分`,
        4
      );
    } else {
      showNarration(
        '🌌 虚空回响',
        '虚空中传来回音，但无人回应……也许下次会有不同的结果',
        '再次尝试吧',
        3
      );
    }
    loadDashboard();
  } else {
    toast(r.message, 'error');
  }
}

async function doLegion(scale){
  const r = await apiPost('/legion', {scale});
  if(r.success){
    toast(r.message, r.soldiers_obtained > 0 ? 'levelup' : 'info');
    loadDashboard();
  } else {
    toast(r.message, 'error');
  }
}

async function doScanGit(){
  const r = await apiPost('/scan-git', {});
  if(r.success){
    toast(r.message, 'success');
    loadDashboard();
  } else {
    toast(r.message, 'error');
  }
}

async function doScanFiles(){
  const r = await apiPost('/scan-files', {});
  if(r.success){
    toast(r.message, 'success');
    loadDashboard();
  } else {
    toast(r.message, 'error');
  }
}

/* ── Achievements ───────────────────────────────────────── */
async function loadAchievements(){
  const d = await apiGet('/achievements');
  const list = document.getElementById('ach-list');
  let html = '';
  for(const a of d.achievements){
    const cls = a.unlocked ? 'unlocked' : 'locked';
    const icon = a.unlocked ? '🏆' : '🔒';
    html += `<div class="ach-card ${cls}">
      <div class="icon">${icon}</div>
      <div class="name">${a.name}</div>
      <div class="desc">${a.description}</div>
      <div class="reward">+${a.reward_exp} EXP, +${a.reward_gold} 金币</div>
    </div>`;
  }
  list.innerHTML = html;
}

/* ── Shop ───────────────────────────────────────────────── */
async function loadShop(){
  const cat = document.getElementById('shop-cat').value;
  const d = await apiGet('/shop' + (cat ? '?category=' + cat : ''));
  document.getElementById('header-gold').textContent = d.gold;
  const list = document.getElementById('shop-list');
  if(!d.items.length){
    list.innerHTML = '<div class="empty">暂无商品 (提高等级解锁)</div>';
    return;
  }
  const catNames = {consumable:'消耗品',equipment:'装备',appearance:'外观',functional:'功能'};
  let currentCat = null, html = '';
  for(const item of d.items){
    if(item.category !== currentCat){
      currentCat = item.category;
      html += `<div class="card-title mt-16">${catNames[currentCat]||currentCat}</div>`;
    }
    const icon = {consumable:'🧪',equipment:'⚔️',appearance:'👑',functional:'⚙️'}[item.category]||'📦';
    const req = item.level_requirement > 1 ? `<span class="s-req">LV.${item.level_requirement}</span>` : '';
    html += `<div class="shop-item">
      <div class="s-icon">${icon}</div>
      <div class="s-info">
        <div class="s-name">${item.name} ${req}</div>
        <div class="s-desc">${item.description}</div>
      </div>
      <div class="s-price">${item.price} 金币</div>
      <button class="btn btn-sm btn-primary" onclick="doBuy('${item.id}')">购买</button>
    </div>`;
  }
  list.innerHTML = html;
}

async function doBuy(id){
  const r = await apiPost('/buy', {id});
  if(r.success){
    toast(r.message, 'success');
    loadShop();
    loadDashboard();
  } else {
    toast(r.message, 'error');
  }
}

/* ── Army ───────────────────────────────────────────────── */
async function loadArmy(){
  const d = await apiGet('/army');
  const list = document.getElementById('army-list');
  if(!d.soldiers.length){
    list.innerHTML = '<div class="empty">暂无士兵 (使用快捷操作召唤)</div>';
    return;
  }
  let html = '';
  for(let i = 0; i < d.soldiers.length; i++){
    const s = d.soldiers[i];
    html += `<div class="task-item">
      <div class="check" style="background:var(--purple);border:none">${i+1}</div>
      <div class="info">
        <div class="name">${s.name}</div>
        <div class="detail">LV.${s.level} [${s.type}]</div>
      </div>
      <span class="text-dim">${s.obtainedAt||''}</span>
    </div>`;
  }
  list.innerHTML = html;
}

/* ── Dungeons ───────────────────────────────────────────── */
async function loadDungeons(){
  const d = await apiGet('/dungeons');
  const list = document.getElementById('dungeon-list');
  if(!d.dungeons.length){
    list.innerHTML = '<div class="empty">暂无可用副本</div>';
    return;
  }
  let html = '';
  for(const dg of d.dungeons){
    const typeIcon = {daily:'📅',weekly:'🔄',boss:'💀'}[dg.type]||'📋';
    html += `<div class="card">
      <div style="display:flex;align-items:center;gap:12px">
        <span style="font-size:28px">${typeIcon}</span>
        <div style="flex:1">
          <div style="font-size:16px;font-weight:700">${dg.name}</div>
          <div class="text-dim">${dg.description} (${dg.type})</div>
        </div>
        <button class="btn btn-primary" onclick="doEnterDungeon('${dg.id}')">进入</button>
      </div>
      <div class="btn-group">
        ${dg.tasks.map(t => `<span class="text-dim">${t.name} (${t.type} x${t.target})</span>`).join(' · ')}
      </div>
    </div>`;
  }
  list.innerHTML = html;
}

async function doEnterDungeon(id){
  const r = await apiPost('/enter-dungeon', {id});
  if(r.success){
    const inst = r.instance;
    // Show cinematic narrative for dungeon entry
    const taskNames = inst.tasks.map(t => t.name).join('、');
    showNarration(
      `🏰 ${inst.dungeon_name}`,
      `难度 ${inst.difficulty} — 挑战 ${inst.tasks.length} 项任务`,
      `${taskNames} | 总奖励 ${inst.total_reward} EXP | +${r.entry_exp} EXP (入场)`,
      5
    );
    loadDashboard();
  } else {
    toast(r.message, 'error');
  }
}

/* ── Bosses ─────────────────────────────────────────────── */
async function loadBosses(){
  const d = await apiGet('/bosses');
  const list = document.getElementById('boss-list');
  if(!d.bosses.length){
    list.innerHTML = '<div class="empty">暂无可挑战 Boss (需要 LV.10+)</div>';
    return;
  }
  let html = '';
  for(const b of d.bosses){
    const cls = b.defeated ? 'defeated' : '';
    const icon = b.defeated ? '✅' : '💀';
    html += `<div class="boss-card ${cls}">
      <div class="b-icon">${icon}</div>
      <div class="b-info">
        <div class="b-name">${b.name}</div>
        <div class="b-desc">${b.description}</div>
        <div class="b-reward">奖励: ${b.reward_exp} EXP, ${b.reward_gold} 金币</div>
      </div>
      <div style="text-align:center">
        <div class="text-dim" style="font-size:11px">HP</div>
        <div style="font-size:20px;font-weight:700;color:var(--red)">${b.hp}</div>
      </div>
    </div>`;
  }
  list.innerHTML = html;
}

/* ── Integrations ───────────────────────────────────────── */
async function loadIntegrations(){
  const d = await apiGet('/integrations');
  const statusEl = document.getElementById('int-status');
  statusEl.innerHTML = `
    <h3>集成状态</h3>
    <div class="int-row">
      <div class="int-icon">🏃</div>
      <div class="int-info"><div class="int-name">健康数据</div><div class="int-desc">步数/运动/睡眠 → EXP</div></div>
      <span class="int-status ${d.healthEnabled?'on':'off'}">${d.healthEnabled?'已启用':'已停用'}</span>
      <button class="btn btn-sm" onclick="toggleInt('health',${!d.healthEnabled})">${d.healthEnabled?'停用':'启用'}</button>
    </div>
    <div class="int-row">
      <div class="int-icon">📖</div>
      <div class="int-info"><div class="int-name">阅读数据</div><div class="int-desc">阅读时长/页数 → EXP</div></div>
      <span class="int-status ${d.readingEnabled?'on':'off'}">${d.readingEnabled?'已启用':'已停用'}</span>
      <button class="btn btn-sm" onclick="toggleInt('reading',${!d.readingEnabled})">${d.readingEnabled?'停用':'启用'}</button>
    </div>
    <div class="int-row">
      <div class="int-icon">🌐</div>
      <div class="int-info"><div class="int-name">浏览器活动</div><div class="int-desc">学习时长 → EXP</div></div>
      <span class="int-status ${d.browserEnabled?'on':'off'}">${d.browserEnabled?'已启用':'已停用'}</span>
      <button class="btn btn-sm" onclick="toggleInt('browser',${!d.browserEnabled})">${d.browserEnabled?'停用':'启用'}</button>
    </div>
    <div class="text-dim mt-12">总导入次数: ${d.totalImports}</div>
  `;

  const actionsEl = document.getElementById('int-actions');
  actionsEl.innerHTML = `
    <div class="card">
      <h3>🏃 记录健康</h3>
      <div class="input-row"><label>步数</label><input type="number" id="h-steps" value="0" style="width:80px"></div>
      <div class="input-row"><label>运动</label><input type="number" id="h-exercise" value="0" style="width:80px"> <span class="text-dim" style="font-size:12px">分钟</span></div>
      <div class="input-row"><label>睡眠</label><input type="number" id="h-sleep" value="0" step="0.5" style="width:80px"> <span class="text-dim" style="font-size:12px">小时</span></div>
      <button class="btn btn-primary" onclick="doHealth()">记录</button>
    </div>
    <div class="card">
      <h3>📖 记录阅读</h3>
      <div class="input-row"><label>时长</label><input type="number" id="r-minutes" value="0" style="width:80px"> <span class="text-dim" style="font-size:12px">分钟</span></div>
      <div class="input-row"><label>页数</label><input type="number" id="r-pages" value="0" style="width:80px"></div>
      <div class="input-row"><label>书名</label><input type="text" id="r-book" value="" style="width:120px"></div>
      <button class="btn btn-primary" onclick="doReading()">记录</button>
    </div>
    <div class="card">
      <h3>🌐 记录浏览器</h3>
      <div class="input-row"><label>网站</label><input type="text" id="b-site" value="leetcode.com" style="width:120px"></div>
      <div class="input-row"><label>时长</label><input type="number" id="b-minutes" value="30" style="width:80px"> <span class="text-dim" style="font-size:12px">分钟</span></div>
      <button class="btn btn-primary" onclick="doBrowser()">记录</button>
    </div>
  `;
}

async function toggleInt(type, enable){
  const r = await apiPost('/integrations/' + (enable ? 'enable' : 'disable'), {target: type});
  toast(r.message, r.success ? 'success' : 'error');
  if(r.success) loadIntegrations();
}

async function doHealth(){
  const steps = parseInt(document.getElementById('h-steps').value)||0;
  const exercise = parseInt(document.getElementById('h-exercise').value)||0;
  const sleep = parseFloat(document.getElementById('h-sleep').value)||0;
  const r = await apiPost('/health', {steps, exercise_min: exercise, sleep_hours: sleep});
  if(r.success){
    toast(`+${r.total_exp} EXP`, 'success');
    loadDashboard();
  } else {
    toast(r.message, 'error');
  }
}

async function doReading(){
  const minutes = parseInt(document.getElementById('r-minutes').value)||0;
  const pages = parseInt(document.getElementById('r-pages').value)||0;
  const book = document.getElementById('r-book').value;
  const r = await apiPost('/reading', {minutes, pages, book});
  if(r.success){
    toast(`+${r.total_exp} EXP`, 'success');
    loadDashboard();
  } else {
    toast(r.message, 'error');
  }
}

async function doBrowser(){
  const site = document.getElementById('b-site').value;
  const minutes = parseInt(document.getElementById('b-minutes').value)||0;
  const r = await apiPost('/browser', {site, minutes});
  if(r.success){
    toast(`+${r.total_exp} EXP`, 'success');
    loadDashboard();
  } else {
    toast(r.message, 'error');
  }
}

/* ── Guild System ───────────────────────────────────────── */
async function loadGuild(){
  if(!isLoggedIn()){ loadGuildJoinPanel(); return; }

  // Check if user is in a guild
  const my = await apiPost('/guilds/my', {});
  const statusEl = document.getElementById('guild-status');
  const detailEl = document.getElementById('guild-detail');
  const joinEl = document.getElementById('guild-join-panel');
  const rankEl = document.getElementById('guild-rankings');

  if(my.success && my.id){
    // User is in a guild — show detail
    statusEl.innerHTML = `<div class="guild-header">
      <h2>${my.name}</h2>
      <span class="guild-badge member">${my.rank}</span>
      <span class="text-dim">${my.memberCount} 人 | 贡献 ${my.contribution}</span>
    </div>`;
    joinEl.innerHTML = '';
    rankEl.innerHTML = '';
    loadGuildDetail(my);
  } else {
    // Not in a guild — show create/join + rankings
    statusEl.innerHTML = '';
    detailEl.innerHTML = '';
    loadGuildJoinPanel();
    loadGuildRankings();
  }
}

async function loadGuildJoinPanel(){
  const el = document.getElementById('guild-join-panel');
  const d = await apiGet('/guilds');
  let html = '<div class="card"><h3>创建公会</h3><div class="input-row"><input type="text" id="create-guild-name" placeholder="公会名称" style="width:200px"><button class="btn btn-primary" onclick="doCreateGuild()">创建</button></div></div>';
  html += '<div class="card"><h3>加入公会</h3><div class="input-row"><input type="text" id="join-guild-id" placeholder="公会ID" style="width:150px"><button class="btn btn-primary" onclick="doJoinGuild()">加入</button></div></div>';

  if(d.guilds && d.guilds.length){
    html += '<div class="card"><h3>公会列表</h3>';
    for(const g of d.guilds){
      html += `<div class="guild-card">
        <div class="g-rank">${g.rank}</div>
        <div class="g-name">${g.name}</div>
        <div class="g-info">${g.members}/${g.maxMembers} 人 | 贡献: ${g.contribution}</div>
        <button class="btn btn-sm" onclick="document.getElementById('join-guild-id').value='${g.id}';doJoinGuild()">加入</button>
      </div>`;
    }
    html += '</div>';
  }
  el.innerHTML = html;
}

async function loadGuildDetail(my){
  const el = document.getElementById('guild-detail');
  const info = await apiPost('/guilds/info', {guildId: my.id});

  // Active task
  let taskHtml = '';
  if(my.activeTask){
    const t = my.activeTask;
    const pct = Math.min(100, Math.round(t.current / t.target * 100));
    taskHtml = `<div class="card"><h3>公会任务: ${t.name}</h3>
      <div class="text-dim">${t.desc}</div>
      <div class="guild-task-bar"><div class="guild-task-fill" style="width:${pct}%">${t.current}/${t.target}</div></div>
      <div class="input-row" style="margin-top:8px">
        <label>贡献</label>
        <select id="guild-contribute-type">
          ${skillOptionsHtml(s)}
        </select>
        <input type="number" id="guild-contribute-qty" value="1" min="1" style="width:80px">
        <button class="btn btn-primary" onclick="doGuildContribute()">贡献</button>
      </div>
    </div>`;
  } else {
    taskHtml = `<div class="card"><h3>公会任务</h3>
      <div class="text-dim">当前无进行中的任务</div>
      <button class="btn btn-primary" onclick="doStartGuildTask()">开启新任务</button>
    </div>`;
  }

  // Active boss
  let bossHtml = '';
  if(my.activeBoss){
    const b = my.activeBoss;
    const pct = Math.max(0, Math.round(b.currentHp / b.maxHp * 100));
    bossHtml = `<div class="card" style="border-color:var(--red)">
      <h3 style="color:var(--red)">⚔️ Boss 战: ${b.name}</h3>
      <div class="guild-boss-hp"><div class="guild-boss-fill" style="width:${pct}%">${b.currentHp}/${b.maxHp}</div></div>
      <div class="input-row" style="margin-top:8px">
        <label>攻击</label>
        <select id="guild-attack-type">
          ${skillOptionsHtml(s)}
        </select>
        <input type="number" id="guild-attack-qty" value="1" min="1" style="width:80px">
        <button class="btn btn-primary" style="border-color:var(--red);color:var(--red)" onclick="doGuildDealDamage()">攻击</button>
      </div>
    </div>`;
  } else {
    bossHtml = `<div class="card"><h3>Boss 战</h3>
      <div class="text-dim">当前无 Boss 战</div>
      <button class="btn btn-primary" style="border-color:var(--red);color:var(--red)" onclick="doStartGuildBattle()">发起 Boss 战</button>
    </div>`;
  }

  // Members
  let membersHtml = '<div class="card"><h3>成员列表 (' + my.memberCount + '/' + (my.maxMembers || 20) + ')</h3>';
  for(const m of my.members){
    const roleClass = m.role;
    const roleName = {leader:'👑 领袖',officer:'⭐ 副手',member:'成员'}[m.role]||m.role;
    membersHtml += `<div class="guild-member">
      <span class="role ${roleClass}">${roleName}</span>
      <span class="m-info">${m.username}</span>
      <span class="m-contrib">贡献: ${m.contribution||0}</span>
      ${my.id && info && info.leader === info.members.find(x=>x.username===my.id)?.username ?
        `<span class="m-actions">
          ${m.role!=='leader'?`<button class="btn btn-sm" onclick="doPromoteMember('${m.username}')">副手</button>`:''}
          ${m.role!=='leader'?`<button class="btn btn-sm btn-danger" onclick="doKickMember('${m.username}')">踢出</button>`:''}
        </span>` : ''}
    </div>`;
  }
  membersHtml += '</div>';

  // Logs
  let logsHtml = '';
  if(info && info.logs && info.logs.length){
    logsHtml = '<div class="card"><h3>最近动态</h3>';
    for(const l of info.logs.slice(-10).reverse()){
      const time = new Date(l.timestamp).toLocaleString('zh-CN');
      logsHtml += `<div class="guild-log"><span class="time">${time}</span>${l.message}</div>`;
    }
    logsHtml += '</div>';
  }

  // Actions
  let actionsHtml = `<div class="btn-group">
    <button class="btn btn-primary" onclick="doLeaveGuild()">离开公会</button>
  </div>`;

  el.innerHTML = taskHtml + bossHtml + membersHtml + logsHtml + actionsHtml;
}

async function doCreateGuild(){
  const name = document.getElementById('create-guild-name').value.trim();
  if(!name){ toast('请输入公会名称','error'); return; }
  const r = await apiPost('/guilds/create', {name});
  toast(r.message, r.success ? 'success' : 'error');
  if(r.success) loadGuild();
}

async function doJoinGuild(){
  const id = document.getElementById('join-guild-id').value.trim();
  if(!id){ toast('请输入公会ID','error'); return; }
  const r = await apiPost('/guilds/join', {guildId: id});
  toast(r.message, r.success ? 'success' : 'error');
  if(r.success) loadGuild();
}

async function doLeaveGuild(){
  if(!confirm('确定离开公会？')) return;
  const my = await apiPost('/guilds/my', {});
  if(!my.success) return;
  const r = await apiPost('/guilds/leave', {guildId: my.id});
  toast(r.message, r.success ? 'success' : 'error');
  if(r.success) loadGuild();
}

async function doStartGuildTask(){
  const my = await apiPost('/guilds/my', {});
  if(!my.success) return;
  const r = await apiPost('/guilds/start-task', {guildId: my.id});
  toast(r.message, r.success ? 'success' : 'error');
  if(r.success) loadGuild();
}

async function doGuildContribute(){
  const my = await apiPost('/guilds/my', {});
  if(!my.success) return;
  const type = document.getElementById('guild-contribute-type').value;
  const qty = parseInt(document.getElementById('guild-contribute-qty').value)||1;
  const r = await apiPost('/guilds/contribute', {guildId: my.id, actionType: type, quantity: qty});
  toast(r.message || `贡献: ${r.progress}/${r.target}`, r.completed ? 'levelup' : 'success');
  if(r.rewards){
    for(const [u, rw] of Object.entries(r.rewards)){
      toast(`${u}: +${rw.exp} EXP, +${rw.gold} 金币`, 'success');
    }
  }
  loadGuild();
}

async function doStartGuildBattle(){
  const my = await apiPost('/guilds/my', {});
  if(!my.success) return;
  const r = await apiPost('/guilds/start-battle', {guildId: my.id});
  toast(r.message, r.success ? 'success' : 'error');
  if(r.success) loadGuild();
}

async function doGuildDealDamage(){
  const my = await apiPost('/guilds/my', {});
  if(!my.success) return;
  const type = document.getElementById('guild-attack-type').value;
  const qty = parseInt(document.getElementById('guild-attack-qty').value)||1;
  const r = await apiPost('/guilds/deal-damage', {guildId: my.id, actionType: type, quantity: qty});
  toast(r.message || `造成 ${r.damage} 伤害 (HP: ${r.bossHp}/${r.bossMaxHp})`, r.defeated ? 'levelup' : 'success');
  if(r.rewards){
    for(const [u, rw] of Object.entries(r.rewards)){
      toast(`${u}: +${rw.exp} EXP, +${rw.gold} 金币`, 'success');
    }
  }
  loadGuild();
}

async function doPromoteMember(username){
  if(!confirm(`任命 ${username} 为副手？`)) return;
  const my = await apiPost('/guilds/my', {});
  if(!my.success) return;
  const r = await apiPost('/guilds/promote', {guildId: my.id, target: username});
  toast(r.message, r.success ? 'success' : 'error');
  if(r.success) loadGuild();
}

async function doKickMember(username){
  if(!confirm(`踢出 ${username}？`)) return;
  const my = await apiPost('/guilds/my', {});
  if(!my.success) return;
  const r = await apiPost('/guilds/kick', {guildId: my.id, target: username});
  toast(r.message, r.success ? 'success' : 'error');
  if(r.success) loadGuild();
}

async function loadGuildRankings(){
  const el = document.getElementById('guild-rankings');
  const d = await apiGet('/guilds/rankings');
  if(!d.rankings || !d.rankings.length){
    el.innerHTML = '<div class="card"><div class="empty">暂无公会</div></div>';
    return;
  }
  let html = '<div class="card"><h3>公会排行榜</h3>';
  for(let i = 0; i < d.rankings.length; i++){
    const g = d.rankings[i];
    const medal = i===0?'🥇':i===1?'🥈':i===2?'🥉':'';
    html += `<div class="guild-card">
      <span style="font-size:18px;width:24px">${medal||'#'+(i+1)}</span>
      <div class="g-rank">${g.rank}</div>
      <div class="g-name">${g.name}</div>
      <div class="g-info">${g.members} 人 | 贡献: ${g.contribution}</div>
    </div>`;
  }
  html += '</div>';
  el.innerHTML = html;
}

/* ── Analytics ────────────────────────────────────────────── */
function barChart(pct){
  const w = 30;
  const filled = Math.round(pct / 100 * w);
  const empty = w - filled;
  return '<span style="color:var(--green)">' + '█'.repeat(filled) + '</span>' + '<span style="color:var(--border)">' + '░'.repeat(empty) + '</span>';
}

async function loadAnalytics(){
  // Weekly report
  const weekly = await apiGet('/analytics/weekly');
  const dailyNames = {1:'周一',2:'周二',3:'周三',4:'周四',5:'周五',6:'周六',0:'周日'};
  let chartHtml = '';
  const maxExp = Math.max(1, ...weekly.daily_data.map(d => d.exp));
  for(const d of weekly.daily_data){
    const dDate = new Date(d.date + 'T00:00:00');
    const dayName = dailyNames[dDate.getDay()] || '';
    const pct = Math.round(d.exp / maxExp * 100);
    chartHtml += `<div class="stat-row"><span class="stat-label">${dayName||d.date}</span><span class="stat-value">${d.exp} EXP</span><div class="bar-wrap stat-bar" style="height:12px;flex:1"><div class="bar-fill exp" style="width:${pct}%"></div></div></div>`;
  }
  const trendIcon = weekly.trend==='up'?'📈':weekly.trend==='down'?'📉':'➡️';
  const trendLabel = weekly.trend==='up'?'上升':weekly.trend==='down'?'下降':'稳定';
  document.getElementById('analytics-weekly').innerHTML = `
    <h3>📊 本周周报</h3>
    <div class="grid-3" style="margin-bottom:12px">
      <div class="stat-big"><div class="value">${weekly.total_exp}</div><div class="label">总 EXP</div></div>
      <div class="stat-big"><div class="value" style="color:var(--orange)">${weekly.total_gold}</div><div class="label">总金币</div></div>
      <div class="stat-big"><div class="value" style="color:var(--cyan)">${weekly.days_active}/7</div><div class="label">活跃天数</div></div>
    </div>
    <div style="font-size:13px;margin-bottom:8px">趋势: ${trendIcon} ${trendLabel} | 日均: ${weekly.avg_daily_exp} EXP</div>
    ${chartHtml}
  `;

  // Insights
  const insights = await apiGet('/analytics/insights');
  let insHtml = '<h3>🔮 数据洞察</h3>';
  if(insights.insights && insights.insights.length){
    for(let i = 0; i < Math.min(insights.insights.length, 6); i++){
      insHtml += `<div class="task-item" style="margin-bottom:4px"><div class="info"><div class="name">${i+1}. ${insights.insights[i]}</div></div></div>`;
    }
  } else {
    insHtml += '<div class="text-dim">暂无洞察数据 — 先记录一些活动吧！</div>';
  }
  document.getElementById('analytics-insights').innerHTML = insHtml;

  // Streak
  const streak = await apiGet('/analytics/streak');
  document.getElementById('analytics-streak').innerHTML = `
    <h3>⚡ 连击历史</h3>
    <div class="grid-2" style="margin-bottom:12px">
      <div class="stat-big"><div class="value">${streak.current_streak}</div><div class="label">当前连击(天)</div></div>
      <div class="stat-big"><div class="value" style="color:var(--purple)">${streak.best_streak}</div><div class="label">最佳连击(天)</div></div>
    </div>
    <div class="stat-row"><span class="stat-label">活跃天数</span><span class="stat-value">${streak.active_days}/${streak.days_since_created}</span></div>
    <div class="bar-wrap" style="margin-top:8px"><div class="bar-fill exp" style="width:${streak.completion_rate}%"></div></div>
    <div class="text-dim" style="font-size:12px;margin-top:4px">完成率: ${streak.completion_rate}%</div>
  `;

  // Breakdown
  const breakdown = await apiGet('/analytics/breakdown');
  let breakHtml = '<h3>📊 最近30天活动分布</h3>';
  if(breakdown.types && breakdown.types.length){
    const maxTotalExp = Math.max(1, ...breakdown.types.map(t => t.total_exp));
    for(const t of breakdown.types){
      const pct = Math.round(t.total_exp / maxTotalExp * 100);
      breakHtml += `<div class="stat-row">
        <span class="stat-label">${t.type}</span>
        <span class="stat-value">${t.total_exp} EXP (${t.days_active}天, 日均${t.avg_per_day})</span>
        <div class="bar-wrap stat-bar" style="height:12px;flex:1"><div class="bar-fill exp" style="width:${pct}%"></div></div>
      </div>`;
    }
  } else {
    breakHtml += '<div class="text-dim">暂无活动数据</div>';
  }
  document.getElementById('analytics-breakdown').innerHTML = breakHtml;

  // Smart reminders
  apiGet('/analytics/reminders').then(rem => {
    let remHtml = '<h3>🔔 智能提醒</h3>';
    if(rem.reminders && rem.reminders.length){
      remHtml += rem.reminders.map((r, i) =>
        `<div class="task-item" style="margin-bottom:4px"><div class="info"><div class="name">${i+1}. ${r}</div></div></div>`
      ).join('');
    } else {
      remHtml += '<div class="text-dim">暂无提醒</div>';
    }
    document.getElementById('analytics-reminders').innerHTML = remHtml;
  }).catch(() => {
    document.getElementById('analytics-reminders').innerHTML = '<h3>🔔 智能提醒</h3><div class="text-dim">暂不可用</div>';
  });
}

/* ── Init ───────────────────────────────────────────────── */
if(isLoggedIn()){
  showAuthOverlay(false);
  checkOnboarding();
  connectSSE();
  // For returning users who already onboarded but haven't seen the guide
  if(!localStorage.getItem(GUIDE_STORAGE)){
    // Delay slightly so onboarding doesn't interfere
    setTimeout(() => {
      apiGet('/onboard/status').then(r => {
        if(r.onboarded) showGuide();
      }).catch(() => {});
    }, 1500);
  }
} else {
  showAuthOverlay(true);
  showLogin();
}

/* Auto-refresh status every 30s */
setInterval(() => {
  const activeTab = document.querySelector('.tab-content.active');
  if(activeTab){
    const tabId = activeTab.id.replace('tab-','');
    if(tabId==='dashboard') loadDashboard();
    else if(tabId==='tasks') loadTasks();
  }
}, 30000);
