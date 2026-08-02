/* ── SSE Events + Narrative Overlay ────────────────────── */
let eventSource = null;

function connectSSE(){
  try {
  if(eventSource){ eventSource.close(); eventSource = null; }
  const t = getToken();
  if(!t) return;
  const evtSource = new EventSource(API + '/events');
  eventSource = evtSource;
  const feedEl = document.getElementById('event-feed');
  feedEl.classList.add('visible');
  setTimeout(() => { if(eventSource === evtSource) feedEl.classList.remove('visible'); }, 10000);

  evtSource.addEventListener('message', (e) => {
    try {
      const data = JSON.parse(e.data);
      const div = document.createElement('div');
      div.className = 'evt';
      div.innerHTML = `<span class="evt-type">${e.type||'event'}</span><span class="evt-data">${JSON.stringify(data).substring(0,120)}</span>`;
      feedEl.prepend(div);
      while(feedEl.children.length > 50) feedEl.removeChild(feedEl.lastChild);
      feedEl.classList.add('visible');
      setTimeout(() => feedEl.classList.remove('visible'), 5000);
    } catch(err) {}
  });

  /* ── Smart reminder toast ───────────────────────────── */
  evtSource.addEventListener('reminder', (e) => {
    try {
      const d = JSON.parse(e.data);
      const rem = d.reminders || [];
      if(rem.length === 0) return;
      const msg = rem[0];
      // Show in event feed
      const div = document.createElement('div');
      div.className = 'evt';
      div.innerHTML = `<span class="evt-type reminder">⏰ 提醒</span><span class="evt-data">${msg.substring(0, 80)}</span>`;
      feedEl.prepend(div);
      while(feedEl.children.length > 50) feedEl.removeChild(feedEl.lastChild);
      feedEl.classList.add('visible');
      setTimeout(() => feedEl.classList.remove('visible'), 8000);
      // Also show as narration overlay if not in analytics tab
      if(!document.getElementById('tab-analytics').classList.contains('active')){
        showNarration('⏰ ' + msg.substring(0, 24), msg, '暗影君主的提醒', 6);
      }
    } catch(err) {}
  });
  evtSource.onerror = () => {
    evtSource.close(); eventSource = null;
    setTimeout(connectSSE, 5000);
  };
  } catch(e) { console.warn('connectSSE failed:', e); }
}

/* ── Narrative Overlay ──────────────────────────────────── */
let narTimer = null;
function showNarration(title, body, sub, duration){
  duration = duration || 4;
  const el = document.getElementById('narrative-overlay');
  const tEl = document.getElementById('narrative-title');
  const bEl = document.getElementById('narrative-body');
  const sEl = document.getElementById('narrative-sub');
  el.classList.remove('fade-out', 'hidden-nar');
  tEl.className = ''; bEl.className = ''; sEl.className = '';
  tEl.textContent = title; bEl.textContent = body; sEl.textContent = sub || '';
  el.style.display = 'flex';
  void el.offsetWidth; el.classList.add('show'); void el.offsetWidth;
  requestAnimationFrame(() => {
    tEl.classList.add('narrate-title-anim');
    bEl.classList.add('narrate-body-anim');
    sEl.classList.add('narrate-sub-anim');
  });
  if(narTimer) clearTimeout(narTimer);
  narTimer = setTimeout(hideNarration, duration * 1000);
}

function hideNarration(){
  if(narTimer) clearTimeout(narTimer);
  narTimer = null;
  const el = document.getElementById('narrative-overlay');
  el.classList.remove('show'); el.classList.add('fade-out');
  setTimeout(() => {
    el.classList.add('hidden-nar'); el.classList.remove('fade-out');
    document.getElementById('narrative-title').className = '';
    document.getElementById('narrative-body').className = '';
    document.getElementById('narrative-sub').className = '';
  }, 600);
}

/* ── Narrative Text Pools (skill-themed atmospheric text) ── */
const NAR = {
  guitar: {
    record: [
      {t:'🎸 琴音起', b:'你的手指在琴弦间游走，音符如月光般流淌在暗影之中'},
      {t:'🎵 和弦共鸣', b:'每一个和弦都蕴含着力量，琴声穿透了黑暗，唤醒了远古的回响'},
      {t:'🎶 弦外之音', b:'指尖的茧是时间的勋章，每一次拨弦都比上次更加从容'},
    ],
    dungeon: [{t:'🏰 音律神殿', b:'你推开一扇古老的木门，里面传来千年前乐师的琴声'}],
    levelup: [{t:'🎶 琴技突破', b:'你的指尖仿佛被赋予了灵性，一段全新的旋律自然流淌而出'}],
  },
  piano: {
    record: [
      {t:'🎹 黑白键舞', b:'黑白琴键在你指尖下奏响，每一个音符都化作金色的能量'},
      {t:'🎵 月光奏鸣', b:'肖邦的月光在你手中重现，暗影之力随着旋律升腾'},
    ],
    dungeon: [{t:'🏰 钢琴圣殿', b:'巨大的三角钢琴在黑暗中发光——挑战者，用你的琴技证明实力'}],
    levelup: [{t:'🎹 突破', b:'你的手指在琴键上飞舞，突破的快感如同完美的和弦'}],
  },
  coding: {
    record: [
      {t:'💻 代码构筑', b:'指尖敲击键盘，代码如符文般在屏幕上凝结，构筑着暗影帝国的基石'},
      {t:'⌨️ 逻辑之光', b:'每一个函数都是一道符咒，每一行代码都在重塑世界的规则'},
      {t:'🔧 架构觉醒', b:'你看到了代码深处的结构，像暗影君主一样洞察一切'},
    ],
    dungeon: [{t:'🏰 代码迷宫', b:'无数行代码交织成迷宫——只有最纯粹的逻辑才能找到出口'}],
    levelup: [{t:'💻 架构突破', b:'你看到了全新的代码结构，如同暗影帝国在你眼前展开'}],
  },
  commit: {
    record: [
      {t:'🔀 符文铭刻', b:'你的每一次提交都在暗影之书上添上新的符文'},
      {t:'📦 版本之力', b:'Git 仓库深处传来回响，你的代码被永远铭刻在暗影档案中'},
    ],
    dungeon: [{t:'🏰 提交试炼', b:'无数待提交的代码在黑暗中等待——在时限内完成你的提交'}],
    levelup: [{t:'🔀 提交大师', b:'你的每一次 commit 都让暗影帝国更加稳固'}],
  },
  vocabulary: {
    record: [
      {t:'📚 词汇觉醒', b:'每一个单词都是一把钥匙，正在打开暗影知识的门扉'},
      {t:'🔤 语感涌现', b:'陌生的词汇在你脑海中化为熟悉的力量，暗影语法的奥义渐显'},
    ],
    dungeon: [{t:'🏰 单词深渊', b:'无边的词汇深渊在你脚下展开——在迷失之前记住它们'}],
    levelup: [{t:'📚 语感突破', b:'你的词汇量突破了临界点，暗影古文在你眼前清晰可见'}],
  },
  reading: {
    record: [
      {t:'📖 书页翻动', b:'古老的卷轴在你手中展开，暗影知识如泉水般涌入你的意识'},
      {t:'📜 知识之力', b:'每一个段落都蕴藏着力量，你在字里行间找到了暗影的真相'},
    ],
    dungeon: [{t:'🏰 阅读殿堂', b:'巨大的图书馆在你面前展开——每一本书都是一道试炼'}],
    levelup: [{t:'📖 知识突破', b:'你读懂了暗影之书最深奥的一章，知识的力量在你体内汇聚'}],
  },
  exercise: {
    record: [
      {t:'💪 体魄燃烧', b:'汗水是暗影君主的印记，每一次运动都在锻造更强的自己'},
      {t:'🔥 力量涌动', b:'肌肉在暗影中苏醒，力量如潮水般涌遍全身'},
      {t:'⚡ 体力突破', b:'你感受到了体内潜藏的力量正在被一点点唤醒'},
    ],
    dungeon: [{t:'🏰 体魄试炼', b:'体能试炼场在暗影中展开——挑战你的身体极限'}],
    levelup: [{t:'💪 力量突破', b:'你的身体突破了限制，暗影之力在肌肉中奔涌'}],
  },
  running: {
    record: [
      {t:'🏃 风之步伐', b:'你的脚步在暗影中踏出，风声在耳边呼啸，速度就是力量'},
      {t:'💨 疾风前行', b:'每一步都在超越过去的自己，暗影的风在你脚下汇聚'},
    ],
    dungeon: [{t:'🏰 疾风试炼', b:'无限延伸的暗影跑道在你脚下——在疲惫之前到达终点'}],
    levelup: [{t:'🏃 速度突破', b:'你的速度突破了极限，暗影之风都在追赶你的脚步'}],
  },
  yoga: {
    record: [{t:'🧘‍♀️ 柔韧觉醒', b:'你的身体在暗影中舒展，每一个体式都在释放内在的力量'}],
    dungeon: [{t:'🏰 瑜伽圣殿', b:'古老的瑜伽室在暗影中发光——挑战你的柔韧极限'}],
    levelup: [{t:'🧘‍♀️ 柔韧突破', b:'你的身体达到了前所未有的柔韧境界'}],
  },
  meditation: {
    record: [
      {t:'🧘 正念觉醒', b:'你闭上双眼，暗影之力在冥想中汇聚，心灵的力量无限延伸'},
      {t:'☯️ 心如止水', b:'在暗影的深处，你找到了内心的平静——力量从宁静中诞生'},
    ],
    dungeon: [{t:'🏰 冥想殿堂', b:'古老的冥想室在你眼前展开——在暗影中找到你的内心'}],
    levelup: [{t:'🧘 冥想突破', b:'你的意识突破了暗影的束缚，进入了全新的境界'}],
  },
  drawing: {
    record: [{t:'🎨 色彩觉醒', b:'你的画笔在暗影中舞动，每一笔都在创造新的世界'}],
    dungeon: [{t:'🏰 暗影画廊', b:'无数画布在暗影中等待——用你的画笔完成试炼'}],
    levelup: [{t:'🎨 画技突破', b:'你的画笔突破了次元，暗影的色彩在你手中流转'}],
  },
  writing: {
    record: [{t:'✍️ 文字之力', b:'你的笔尖在纸上流淌，每一个字都蕴含着暗影的力量'}],
    dungeon: [{t:'🏰 暗影书房', b:'无数待写的文字在暗影中等待——用你的笔完成试炼'}],
    levelup: [{t:'✍️ 笔力突破', b:'你的文字突破了暗影的束缚，达到了全新的境界'}],
  },
  math: {
    record: [{t:'🔢 公式觉醒', b:'数学公式在你眼前展开，每一个定理都是暗影法则的投影'}],
    dungeon: [{t:'🏰 数学迷宫', b:'几何与代数的迷宫——只有最严密的逻辑才能找到出口'}],
    levelup: [{t:'🔢 定理突破', b:'一道困扰已久的难题在你眼前豁然开朗'}],
  },
  english_speaking: {
    record: [{t:'🗣️ 语音觉醒', b:'你张开嘴，流利的暗影之语自然涌出，如同与生俱来的天赋'}],
    dungeon: [{t:'🏰 语言神殿', b:'无数语言学家在虚空中等待——用你的口语通过试炼'}],
    levelup: [{t:'🗣️ 语音突破', b:'你的英语口语突破了次元壁，流利如暗影之风'}],
  },
  swimming: {
    record: [{t:'🏊 水之力', b:'你在暗影之水中穿梭，每一划都在汇聚力量'}],
    dungeon: [{t:'🏰 深渊水域', b:'无尽的暗影水域在你面前展开——在窒息之前完成挑战'}],
    levelup: [{t:'🏊 泳技突破', b:'你在水中如鱼得水，暗影的潮汐在你手中掌控'}],
  },
  cooking: {
    record: [{t:'🍳 烹饪之力', b:'火焰在暗影中升腾，每一道菜都是对味蕾的献祭'}],
    dungeon: [{t:'🏰 暗影厨房', b:'古老的厨房在暗影中等待——用你的厨艺通过试炼'}],
    levelup: [{t:'🍳 厨艺突破', b:'你的厨艺突破了暗影的限制，达到了全新的境界'}],
  },
  _default: {
    record: [
      {t:'⚡ 暗影修炼', b:'你在暗影中修炼，力量随着每一次练习而增长'},
      {t:'🌟 突破自我', b:'每一次坚持都让暗影之力更加凝聚，你在向着更高的境界迈进'},
    ],
    dungeon: [{t:'🏰 修行试炼', b:'暗影试炼场在你面前展开——用你的技能通过挑战'}],
    levelup: [{t:'⬆️ 突破', b:'你感受到了暗影之力的涌动，新的境界在向你敞开'}],
  },
};

function getSkillNarrative(skillId, action){
  const pool = NAR[skillId];
  if(pool && pool[action]) return pool[action];
  return NAR._default[action] || NAR._default.record;
}
function pickRandom(arr){ return arr[Math.floor(Math.random() * arr.length)]; }
