// ======================================================================
// main.js -- the page's content and the code that renders it. Loaded at the end of index.html's body.
// CONTENT. Everything the page shows is here; edit these, not the markup.
// ======================================================================

var PROFILE = {
  name: 'Luke Zhang',
  initials: 'LZ',
  // 4:5 portrait, 360 x 450, shown up to 240 px wide. Bump ?v= whenever the photo changes:
  // GitHub Pages lets browsers reuse a cached image for 10 minutes, so the old one would linger.
  photo: 'headshot.jpg?v=2',
  school: 'Northeastern University',
  program: 'CS and Business Administration',
  status: 'Open to Summer 2027 internships',
  role: '<strong>Computer Science and Business Administration</strong> at Northeastern University. Backend, data, machine learning, and Python + AI.',
  lede: 'I build systems that can show their working: every project below has a live demo that runs in your browser, a write-up of how it works and what went wrong, and a test suite that checks its own published numbers.',
  bio: [
    "I'm a first-year <strong>Computer Science and Business Administration</strong> student at Northeastern University, graduating in 2030, on a Dean's Scholarship.",
    'My work sits where software meets measurement: <strong>routing and search</strong>, <strong>backend systems</strong>, and <strong>machine learning</strong> that has been benchmarked for fairness. Each project ships with a test suite, a browser demo and an honest account of its limits.',
    "I'm looking for <strong>Summer 2027 internships</strong> in software engineering, AI/ML or data, and I'm happy to talk through any of the work below."
  ],
  focus: [
    ['Backend and APIs', 'Flask REST APIs, JWT and role-based access, relational schema design'],
    ['Data and evaluation', 'pandas pipelines, reproducible benchmarks, statistical agreement'],
    ['Machine learning and vision', 'scikit-learn, OpenCV, fairness benchmarking'],
    ['Algorithms', 'shortest paths, game-tree search, scheduling']
  ],
  links: [
    { label: 'GitHub', url: 'https://github.com/luke-zhang-cs-py', icon: 'github' },
    { label: 'LinkedIn', url: 'https://www.linkedin.com/in/luke-zhang-nu/', icon: 'linkedin' },
    { label: 'Email', url: 'mailto:zhang.l17@northeastern.edu', icon: 'mail' }
  ],
  email: 'zhang.l17@northeastern.edu'
};

var PAGES = 'https://luke-zhang-cs-py.github.io/';
var REPO = 'https://github.com/luke-zhang-cs-py/';

// In impact: data-tests marks the project's own test count, which the hero adds up; data-derived
// marks a figure that is a sum of several in the project's README, so the page's figure check skips it.
var PROJECTS = [
  {
    id: 'transit', featured: true, title: 'Toronto Transit Reach', kind: 'Routing · geospatial', since: '2026-07', dates: 'Jul 2026 – Present',
    categories: ['Algorithms', 'Backend', 'Geospatial'],
    summary: "An isochrone map and time-dependent trip planner for Toronto: click anywhere and see how far you can get in 30 minutes, over the TTC's own timetable and live feed.",
    problem: "Transit maps show lines, not time. You can't see how far 30 minutes gets you from a given corner of Toronto, or when you'd really arrive.",
    approach: "A weighted multi-modal graph searched with Dijkstra over the TTC's GTFS timetable and live GTFS-realtime feed. Every wait says whether it's timetabled, measured live or modelled, and closed lines drop out of the graph.",
    result: 'Reach from any point is computed live in the page: 247 stops within an hour of one start. The browser build is checked stop by stop against the Python and refuses to publish on any disagreement.',
    features: [
      "Shortest-path routing with Dijkstra's algorithm over a weighted multi-modal graph (adjacency list, binary heap).",
      'Every wait is labelled by source: the next timetabled departure, half the live observed headway, or a modelled figure.',
      'Live service alerts remove closed lines from the graph, so trips route around them.',
      'The browser demo is a JavaScript port of the Python search; the build refuses to publish if they disagree at any stop.'
    ],
    impact: [{ html: '<b>516</b> stops verified Python vs JS' }, { html: '<b data-tests>315</b> tests · <b>100%</b> coverage' }],
    tags: ['Python', 'Flask', 'REST API', 'Leaflet', 'GTFS-realtime', 'JavaScript'],
    demo: PAGES + 'Toronto-Transit-Distance-Matrix/app/',
    more: [{ label: 'Write-up', url: PAGES + 'Toronto-Transit-Distance-Matrix/' }],
    source: REPO + 'Toronto-Transit-Distance-Matrix',
    commits: 44,
    gif: { src: PAGES + 'Toronto-Transit-Distance-Matrix/demo.gif', w: 760, h: 478,
           alt: 'Dragging the time filter from 5 to 60 minutes: the reach spreads from a single stop to 247 of them, 30 km out' }
  },
  {
    id: 'almanac', title: 'Almanac', kind: 'Full stack · scheduling', since: '2026-08', dates: 'Aug 2026 – Present',
    categories: ['Backend', 'Full stack'],
    summary: "A calendar and the multi-role booking platform behind it: clients book a provider's free slots, and invites become bookings without the guest making an account.",
    features: [
      'RESTful API with JWT authentication and role-based access control for clients, providers and admins.',
      "Relational schema on SQLite or PostgreSQL; a table lock and a partial unique index mean two people racing for one time can't both win it.",
      'Availability computed from recurring weekly hours, blocked dates and bookings; five kinds of email, each sent exactly once.',
      'Refuses to start in production with the committed development secret that signs every session.'
    ],
    impact: [{ html: '<b data-tests>655</b> tests · <b>100%</b> of 2,733 statements' }, { html: '<b>21</b> scenarios verified Python vs JS' }],
    tags: ['Python', 'Flask', 'JWT', 'RBAC', 'PostgreSQL', 'SQLite', 'SMTP'],
    demo: PAGES + 'Almanac-Main-Full-Stack-Calendar/app/',
    more: [{ label: 'Blank calendar', url: PAGES + 'Almanac-Main-Full-Stack-Calendar/calendar.html' }, { label: 'Write-up', url: PAGES + 'Almanac-Main-Full-Stack-Calendar/' }],
    source: REPO + 'Almanac-Main-Full-Stack-Calendar',
    commits: 48,
    gif: { src: PAGES + 'Almanac-Main-Full-Stack-Calendar/demo.gif', w: 900, h: 700,
           alt: 'Five set-ups running through the same slot engine: a full week, a block that clips one slot, an afternoon blocked off, a day booked solid, and today with the morning gone' }
  },
  {
    id: 'chess', title: 'Dvoretsky Lab', kind: 'Game engine · search', since: '2026-09', dates: 'Sep 2026 – Present',
    categories: ['Algorithms', 'Frontend'],
    summary: "A chess training room built from one player's own Lichess games: an opponent that plays like you, drills cut from your mistakes, and Stockfish grading every move.",
    features: [
      'A chess engine from scratch: 0x88 move generation, alpha-beta with quiescence, a Zobrist transposition table and null-move pruning.',
      "A \"mirror\" opponent that loses centipawns at the player's own rate and answers from their opening repertoire.",
      'Stockfish 19 in a Web Worker grades each move; mistakes are mined by winning chances and scheduled as spaced-repetition drills.',
      "Tested like an engine: perft against Stockfish's counts, SPRT between versions, EPD suites and matches against reference engines, with every one of the code's 4,938 lines, 4,394 statements and 3,551 branches run by the checks."
    ],
    impact: [{ html: 'perft on <b>21</b> positions' }, { html: '<b>+83.5</b> Elo by SPRT' }, { html: 'about <b>1730</b> against Stockfish and Maia' },
             { html: '<b data-tests data-derived title="96 regression, 84 app, 66 rules, 43 titled-player, 32 analysis, 30 sparring, 30 Stockfish 19, 29 coach, 23 engine, 22 integration, 40 perft, 222 browser and 6 single-file checks">723</b> checks' }],
    tags: ['JavaScript', 'Web Workers', 'Stockfish', 'UCI', 'Lichess API', 'Playwright'],
    demo: PAGES + 'Dvoerstky-AI-Chess-Coach/',
    more: [{ label: 'Guide', url: REPO + 'Dvoerstky-AI-Chess-Coach/blob/main/notes/GUIDE.md' }],
    source: REPO + 'Dvoerstky-AI-Chess-Coach',
    commits: 30,
    gif: { src: PAGES + 'Dvoerstky-AI-Chess-Coach/docs/demo.gif', w: 960, h: 795,
           alt: 'The Strength tab re-measuring as the window narrows to 30 days, then a sparring game in which Stockfish grades 3.Bc4 a blunder' }
  },
  {
    id: 'ipo', title: 'IPO Bot', kind: 'LLM agent · finance', since: '2026-10', dates: 'Oct 2026 – Present',
    categories: ['AI agents', 'Data', 'Backend'],
    summary: 'IPO and stock research on Claude that answers in a one-page memo, then lets code check every number in it.',
    features: [
      'A tool-using agent over SEC EDGAR, XBRL financials, FRED and market data, with every calculation done in a calculator tool.',
      'Eleven accuracy checks before each answer, and a KEY NUMBERS block that verify.py recomputes: market cap, EV, multiples and scenario maths.',
      'Portfolio mode sizes a buy by the smallest of the limits in your own rules; the browser demo is the same code, tested against the Python down to how each one reads the JSON in a memo.',
      'A browser terminal lists every NYSE ticker the SEC lists, draws the bull, base and bear cases of a memo as a price projection: 2,000 simulated paths with 10-90% bands, the stop-working price and the rating they imply, and ranks trade ideas by expected return, reward to risk or chance of hitting the stop.',
      'Benchmarked against seven prediction algorithms with permutation tests, a false-discovery correction, a holdout and trading costs.',
      'A keyless prediction bot on a GitHub Actions schedule: S&P 500 prices and the IPO pipeline from public sources, stored point-in-time in SQLite with index membership as it stood on each day (renames and departed stocks included), scored against baselines with Diebold-Mariano tests. On 1.2 million out-of-sample stock predictions it finds no edge, and reports that.',
      'An accuracy audit recomputed its numbers independently and hunted for look-ahead: the fixes made every IPO feature point-in-time and taught the leakage test to catch four planted leaks. The pre-listing IPO model scores PR-AUC 0.682 against a 0.417 base rate, and the report shows that the price-range revision alone gets 0.667.'
    ],
    impact: [{ html: '<b data-tests>786</b> tests' }, { html: '<b>11</b> accuracy checks per memo' }, { html: '<b>0 of 36</b> simple signals survive the correction' }, { html: '<b>100%</b> line and branch coverage' }],
    tags: ['Python', 'Claude API', 'Tool use', 'SEC EDGAR', 'SQLite', 'GitHub Actions', 'JavaScript', 'pytest'],
    demo: PAGES + 'IPO-and-Equity-Research-Agent/app/',
    more: [{ label: 'Write-up', url: PAGES + 'IPO-and-Equity-Research-Agent/' }],
    source: REPO + 'IPO-and-Equity-Research-Agent',
    commits: 73,
    gif: { src: PAGES + 'IPO-and-Equity-Research-Agent/demo.gif', w: 960, h: 600,
           alt: 'A price projection with bull, base and bear paths and 10-90% bands, then sizing a purchase as the stop-working price moves, then the memo checker catching a rating the numbers do not support' }
  },
  {
    id: 'faces', title: 'Face Recognition Attendance', kind: 'Computer vision · fairness', since: '2026-08', dates: 'Aug 2026 – Present',
    categories: ['Computer vision', 'Machine learning', 'Backend'],
    summary: 'A local attendance system: OpenCV reads the webcam, recognises enrolled faces and logs attendance to SQLite. No face data leaves the machine.',
    features: [
      'Detection, LBPH recognition, liveness checks and quality scoring, with a CLI for register, train, run and report.',
      'Benchmarked on all of FairFace: a brightness-based quality gate flagged 38.8% of Black faces against 18.5% of White faces, and was rebuilt to be scale-free.',
      'Match thresholds calibrated by gallery size over 4.77 billion impostor pairs, since a fixed cut fails as enrolment grows.',
      'Tested with no webcam, weights or face data in the repo: 100% of 4,495 statements and every branch run in CI, with mutation testing on the decision, liveness and database code.'
    ],
    impact: [{ html: '<b>97,698</b> faces benchmarked' }, { html: 'detection <b>99.95%</b>' }, { html: 'bias <b>2.15×</b> → <b>1.24×</b>' }, { html: '<b data-tests>1,050</b> tests' }],
    tags: ['Python', 'OpenCV', 'Flask', 'SQLite', 'MediaPipe'],
    demo: PAGES + 'Facial-Recognition-Software/camera/',
    more: [{ label: 'Write-up', url: PAGES + 'Facial-Recognition-Software/' }],
    source: REPO + 'Facial-Recognition-Software',
    commits: 72,
    gif: { src: PAGES + 'Facial-Recognition-Software/demo.gif', w: 900, h: 570,
           alt: 'A face tracked live: the instruction changes from No face detected to Move closer to Head upright to Ready, then a second person appears and the verdict becomes One person only' }
  },
  {
    id: 'spam', title: 'AI Spam Message Classifier', kind: 'Machine learning · NLP', since: '2026-07', dates: 'Jul 2026 – Present',
    categories: ['Machine learning', 'Backend'],
    summary: 'Spam or not, and which words drove the call, with the trained model exported into the page so nothing is uploaded.',
    features: [
      'TF-IDF over unigrams and bigrams, keeping the kind of each noisy token (links, money, short codes) rather than deleting it.',
      'Naive Bayes and logistic regression compared on out-of-fold predictions, with the vectoriser refitted inside every fold.',
      'Decision threshold chosen for the best F1 with precision held at 0.90, and saved inside the model artifact.'
    ],
    impact: [{ html: 'F1 <b>0.850</b> at precision <b>0.90</b>' }, { html: '<b data-tests>229</b> tests · <b>100%</b> coverage' }],
    tags: ['Python', 'scikit-learn', 'pandas', 'Flask', 'JavaScript'],
    demo: PAGES + 'AI-Spam-Message-Classifier/app/',
    more: [{ label: 'Write-up', url: PAGES + 'AI-Spam-Message-Classifier/' }],
    source: REPO + 'AI-Spam-Message-Classifier',
    commits: 22,
    gif: { src: PAGES + 'AI-Spam-Message-Classifier/demo.gif', w: 720, h: 653,
           alt: 'Classifying three messages: a lunch text comes back HAM, a prize message SPAM, and a competition text SPAM at 79.1%, with the words ranked by how much each pushed the verdict' }
  },
  {
    id: 'wallet', title: 'Wallet FX', kind: 'Finance · data', since: '2026-09', dates: 'Sep 2026',
    categories: ['Backend', 'Data'],
    summary: "Euro spending converted to CAD and USD at the rate the European Central Bank published on the day of each purchase, showing what the card's markup really cost.",
    features: [
      "Each purchase is converted at its own day's ECB rate; on weekends and holidays it walks back to the last published day and records the lag, and never reaches forward.",
      "Compares the card's bill with the ECB rate, so a hidden 2.5% conversion fee shows up on every purchase.",
      'Imports from a synced folder, QFX, a CSV in any layout, or a receipt screenshot read by local OCR, and refuses a row rather than guess its currency.',
      'Four layered packages, with the layering asserted by a test instead of left to convention.'
    ],
    impact: [{ html: 'card markup <b>2.49%</b> made visible' }, { html: '<b data-tests>982</b> tests · <b>100%</b> coverage' }],
    tags: ['Python', 'Flask', 'SQLite', 'OCR', 'JavaScript'],
    demo: PAGES + 'Budgeting-EU-US-CAN-Almanac-Branch/app/',
    more: [{ label: 'Receipt capture', url: PAGES + 'Budgeting-EU-US-CAN-Almanac-Branch/capture/' }, { label: 'Write-up', url: PAGES + 'Budgeting-EU-US-CAN-Almanac-Branch/' }],
    source: REPO + 'Budgeting-EU-US-CAN-Almanac-Branch',
    commits: 32,
    gif: { src: PAGES + 'Budgeting-EU-US-CAN-Almanac-Branch/demo.gif', w: 860, h: 552,
           alt: "Four purchases landing one at a time, each converted at the rate published on the day it was spent; the Sunday purchase is marked as using Friday's rate, two days back" }
  },
  {
    id: 'tally', title: 'Tally', kind: 'Mobile-first · product', since: '2026-09', dates: 'Sep 2026',
    categories: ['Frontend', 'Backend'],
    summary: 'A phone-first expense tracker for the seconds after you spend: tap an amount, tap a category, done.',
    features: [
      'A till-style keypad: digits shift in from the right, so there is no decimal point to place.',
      'Anything bought three or more times in 90 days becomes a one-tap button carrying its amount and category.',
      'Money stored as integer cents, and currencies never summed without a rate.',
      'Local only: no account, no bank connection; exports CSV for reconciliation.'
    ],
    impact: [{ html: '<b>2</b> taps for a regular purchase' }, { html: '<b data-tests>279</b> tests' }],
    tags: ['Python', 'Flask', 'SQLite', 'JavaScript'],
    demo: PAGES + 'tally/app/',
    more: [{ label: 'Write-up', url: PAGES + 'tally/' }],
    source: REPO + 'tally',
    commits: 16,
    gif: { src: PAGES + 'tally/demo.gif', w: 470, h: 903,
           alt: "Tapping 3, 5, 0 so the amount shifts in from the right as 3.50, choosing Coffee, saving, then a second entry, the day's total climbing to 15.90 euros" }
  }
];

var SKILLS = [
  ['Languages', ['Python', 'Java', 'JavaScript', 'SQL', 'HTML/CSS']],
  ['Backend and APIs', ['Flask', 'REST API design', 'JWT auth', 'RBAC', 'SMTP email']],
  ['Databases', ['PostgreSQL', 'SQLite', 'Schema design', 'Indexes and constraints', 'Write locks']],
  ['Data and ML', ['pandas', 'NumPy', 'scikit-learn', 'TF-IDF', 'Cross-validation']],
  ['Algorithms', ['Dijkstra', 'Binary heaps', 'Alpha-beta search', 'Zobrist hashing', 'Interval scheduling']],
  ['Computer vision', ['OpenCV', 'LBPH recognition', 'YuNet detection', 'MediaPipe', 'Liveness checks']],
  ['Geospatial and real-time', ['GTFS', 'GTFS-realtime', 'Protobuf', 'Leaflet', 'OpenStreetMap']],
  ['Testing and tooling', ['pytest', 'Playwright', 'GitHub Actions', 'Coverage', 'Web Workers']]
];

// The themes the toggle steps through, in order. Each needs a .theme-<name> block in tokens.css;
// the first is the default, and must match the class written on <html>.
var THEMES = ['dark', 'light'];

// ======================================================================
// RENDERING. The layout below turns the content above into the page.
// ======================================================================
(function () {
  var root = document.documentElement;
  var $ = function (id) { return document.getElementById(id); };
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  var STILL = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';   // a 1x1 transparent GIF
  var ICONS = {
    github: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 .5a11.5 11.5 0 0 0-3.64 22.41c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.53-1.33-1.28-1.69-1.28-1.69-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.56-.29-5.25-1.28-5.25-5.7 0-1.26.45-2.29 1.19-3.1-.12-.29-.52-1.47.11-3.06 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.77.11 3.06.74.81 1.19 1.84 1.19 3.1 0 4.43-2.7 5.4-5.27 5.69.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5z"/></svg>',
    linkedin: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M20.45 20.45h-3.56v-5.57c0-1.33-.02-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28zM5.34 7.43a2.06 2.06 0 1 1 0-4.13 2.06 2.06 0 0 1 0 4.13zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1.73C24 .77 23.2 0 22.22 0z"/></svg>',
    mail: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>'
  };
  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---- hero, about, contact links
  // a link by its label, so reordering PROFILE.links cannot send the command menu to the wrong site;
  // '' when no link has that label (renamed or removed), so the menu leaves the command out instead of throwing
  function linkUrl(label) {
    var link = PROFILE.links.find(function (l) { return l.label === label; });
    return link && link.url ? link.url : '';
  }

  function linkButtons(primary) {
    return (primary ? '<a class="btn primary" href="#projects">View my work</a>' : '') + PROFILE.links.map(function (l) {
      return '<a class="btn" href="' + esc(l.url) + '"' + (l.icon === 'mail' ? '' : ' rel="me"') + '>' + ICONS[l.icon] + esc(l.label) + '</a>';
    }).join('');
  }
  $('heroRole').innerHTML = PROFILE.role;
  $('heroLede').textContent = PROFILE.lede;
  $('heroLinks').innerHTML = linkButtons(true);
  $('contactLinks').innerHTML = linkButtons(false);
  $('avatar').innerHTML = PROFILE.photo ? '<img src="' + esc(PROFILE.photo) + '" alt="' + esc(PROFILE.name) + '">' : '<span aria-hidden="true">' + esc(PROFILE.initials) + '</span>';
  $('who').innerHTML = '<b>' + esc(PROFILE.name) + '</b><span>' + esc(PROFILE.program) + '</span><span>' + esc(PROFILE.school) + '</span>' +
    (PROFILE.status ? '<span class="open">' + esc(PROFILE.status) + '</span>' : '');
  $('bio').innerHTML = PROFILE.bio.map(function (p) { return '<p>' + p + '</p>'; }).join('');
  $('focus').innerHTML = PROFILE.focus.map(function (f) { return '<li class="card"><b>' + esc(f[0]) + '</b><span>' + esc(f[1]) + '</span></li>'; }).join('');

  // ---- the headline figures are counted from the projects, never typed in
  var totalTests = 0;
  var holder = document.createElement('div');
  PROJECTS.forEach(function (p) {
    holder.innerHTML = p.impact.map(function (i) { return i.html; }).join(' ');
    var b = holder.querySelector('[data-tests]');
    if (b) totalTests += +b.textContent.replace(/,/g, '');
  });
  // Commits across the repos, rounded down to a ten and shown with a plus: each project's count is a
  // floor that check_site.py holds to GitHub, so the figure only ever understates.
  var commits = PROJECTS.reduce(function (n, p) { return n + (p.commits || 0); }, 0);
  var allDemo = PROJECTS.every(function (p) { return p.demo; });
  $('stats').innerHTML = [
    [PROJECTS.length, 'open-source projects' + (allDemo ? ' · live demos, no install' : '')],
    [(Math.floor(commits / 10) * 10).toLocaleString('en-US') + '+', 'commits across ' + PROJECTS.length + ' repos', ' data-commits'],
    [totalTests.toLocaleString('en-US'), 'automated tests and checks', ' data-tests-total'],
    ['MIT', 'licensed, CI on every push']
  ].map(function (s) { return '<div class="card"><b' + (s[2] || '') + '>' + s[0] + '</b><span>' + s[1] + '</span></div>'; }).join('');

  // ---- projects
  function demo(p) {
    return '<div class="shot"><picture><source media="(prefers-reduced-motion: reduce)" srcset="' + STILL + '">' +
      '<img src="' + esc(p.gif.src) + '" width="' + p.gif.w + '" height="' + p.gif.h + '" loading="lazy" alt="' + esc(p.gif.alt) + '"></picture>' +
      '<button class="play" type="button" style="--ratio:' + p.gif.w + '/' + p.gif.h + '" aria-label="Play demo: ' + esc(p.title) + '" hidden>▶ Play demo</button></div>';
  }
  function card(p) {
    var list = function (items, cls, label) { return '<ul class="' + cls + '" aria-label="' + label + '">' + items + '</ul>'; };
    var body = '<p class="meta"><span class="kind">' + esc(p.kind) + '</span><time datetime="' + p.since + '">' + esc(p.dates) + '</time></p>' +
      '<h3 id="h-' + p.id + '">' + esc(p.title) + '</h3><p class="pitch">' + esc(p.summary) + '</p>';
    if (p.featured) {
      body += '<details class="inside"><summary>Problem, approach, result</summary><dl class="case">' + [['Problem', p.problem], ['Approach', p.approach], ['Result', p.result]].map(function (c) {
        return '<div><dt>' + c[0] + '</dt><dd>' + esc(c[1]) + '</dd></div>'; }).join('') + '</dl></details>';
    }
    body += '<details class="inside"><summary>What\'s inside</summary><ul>' + p.features.map(function (f) { return '<li>' + esc(f) + '</li>'; }).join('') + '</ul></details>';
    if (p.featured) body = '<div class="half">' + body + '</div><div class="half">';
    body += list(p.impact.map(function (i) { return '<li>' + i.html + '</li>'; }).join(''), 'impact', 'Results') +
      list(p.tags.map(function (t) { return '<li>' + esc(t) + '</li>'; }).join(''), 'tags', 'Technologies') +
      '<div class="links"><a class="btn primary" href="' + esc(p.demo) + '">Live demo</a>' +
      p.more.map(function (m) { return '<a class="btn" href="' + esc(m.url) + '">' + esc(m.label) + '</a>'; }).join('') +
      '<a class="btn" href="' + esc(p.source) + '">Source</a></div>' + (p.featured ? '</div>' : '');
    return '<article class="reveal project' + (p.featured ? ' featured' : '') + '" id="' + p.id + '" aria-labelledby="h-' + p.id + '" data-categories="' +
      esc(p.categories.join('|')) + '">' + demo(p) + '<div class="body">' + body + '</div></article>';
  }
  // the featured card leads, so its two cells always start a row (at three across, eight cards fill three rows)
  $('projectList').innerHTML = '<div class="grid">' + PROJECTS.filter(function (p) { return p.featured; }).concat(
    PROJECTS.filter(function (p) { return !p.featured; })).map(card).join('') + '</div>';

  // ---- the category filter
  var categories = [];
  PROJECTS.forEach(function (p) { p.categories.forEach(function (c) { if (categories.indexOf(c) < 0) categories.push(c); }); });
  categories.sort();
  $('filters').innerHTML = ['All'].concat(categories).map(function (c) {
    return '<button class="chip" type="button" data-filter="' + esc(c) + '" aria-pressed="' + (c === 'All') + '">' + esc(c) + '</button>';
  }).join('');
  function applyFilter(category) {
    var shown = 0;
    document.querySelectorAll('.project').forEach(function (a) {
      var match = category === 'All' || a.dataset.categories.split('|').indexOf(category) > -1;
      a.hidden = !match;
      if (match) { shown++; a.classList.add('in'); }
    });
    document.querySelectorAll('.chip').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.filter === category)); });
    $('projectCount').textContent = category === 'All' ? PROJECTS.length + ' projects'
      : 'Showing ' + shown + ' of ' + PROJECTS.length + ' projects in ' + category;
  }
  $('filters').addEventListener('click', function (e) { var b = e.target.closest('.chip'); if (b) applyFilter(b.dataset.filter); });
  applyFilter('All');

  // ---- skills
  $('skillList').innerHTML = SKILLS.map(function (s) {
    return '<div class="skill card"><h3>' + esc(s[0]) + '</h3><ul>' + s[1].map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') + '</ul></div>';
  }).join('');

  // ---- demo GIFs: <picture> already chose a blank still for visitors who ask for less
  // motion; Play takes that choice away, so the GIF loads.
  if (reducedMotion) {
    document.querySelectorAll('.shot').forEach(function (shot) {
      var img = shot.querySelector('img'), still = shot.querySelector('source'), play = shot.querySelector('.play');
      shot.classList.add('reduced');
      img.hidden = true;
      play.hidden = false;
      play.addEventListener('click', function () { still.remove(); img.hidden = false; play.hidden = true; });
    });
  }

  // ---- theme: a class on <html>, dark until the visitor chooses otherwise. The button steps through
  // THEMES in order; each name needs a matching .theme-<name> block in tokens.css, and the first is
  // the one written into the markup.
  var themeBtn = $('themeBtn');
  var theme = THEMES.filter(function (t) { return root.classList.contains('theme-' + t); })[0] || THEMES[0];
  function nextTheme() { return THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length]; }
  function applyTheme(name) {
    root.className = root.className.replace(/(^|\s)theme-\S+/g, '').trim() + ' theme-' + name;
    theme = name;
    themeBtn.setAttribute('aria-label', 'Switch to ' + nextTheme() + ' theme');
    // the browser's own toolbar colour follows the page
    var bg = getComputedStyle(root).getPropertyValue('--color-bg').trim();
    document.querySelectorAll('meta[name="theme-color"]').forEach(function (m) { m.content = bg; });
  }
  function toggleTheme() {
    var next = nextTheme();
    try { localStorage.setItem('theme', next); } catch (e) { /* not remembered */ }
    applyTheme(next);
  }
  applyTheme(theme);   // also drops a saved theme that no longer exists
  themeBtn.addEventListener('click', toggleTheme);

  // ---- contact: a front-end-only form that hands a finished email to the visitor's mail app
  var form = $('contactForm'), formStatus = $('formStatus');
  var EMAIL_SHAPE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var fields = { name: $('cfName'), email: $('cfEmail'), message: $('cfMessage') };
    var bad = Object.keys(fields).filter(function (k) {
      var v = fields[k].value.trim();
      return !v || (k === 'email' && !EMAIL_SHAPE.test(v));
    });
    Object.keys(fields).forEach(function (k) { fields[k].setAttribute('aria-invalid', String(bad.indexOf(k) > -1)); });
    if (bad.length) {
      formStatus.dataset.kind = 'error';
      formStatus.textContent = bad.indexOf('email') > -1 && fields.email.value.trim() ? 'That email address looks incomplete.' : 'Please fill in your name, email and message.';
      fields[bad[0]].focus();
      return;
    }
    var subject = 'Portfolio: message from ' + fields.name.value.trim();
    var body = fields.message.value.trim() + '\n\n-- ' + fields.name.value.trim() + ' (' + fields.email.value.trim() + ')';
    formStatus.dataset.kind = 'ok';
    formStatus.textContent = "Your email app should open with this message. If it doesn't, write to " + PROFILE.email + '.';
    form.dataset.mailto = 'mailto:' + PROFILE.email + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
    window.location.href = form.dataset.mailto;
  });

  // ---- the command palette: Ctrl/Cmd+K or "/" from anywhere
  var palette = $('palette'), input = $('paletteInput'), listEl = $('paletteList');
  function go(id) { return function () { var el = $(id); el.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth' }); el.classList.add('in'); }; }
  var COMMANDS = [
    { label: 'About', hint: 'section', run: go('about') },
    { label: 'Projects', hint: 'section', run: go('projects') },
    { label: 'Skills', hint: 'section', run: go('skills') },
    { label: 'Contact', hint: 'section', run: go('contact') }
  ].concat(PROJECTS.map(function (p) {
    return { label: p.title, hint: 'project', keywords: p.tags.concat(p.categories).join(' '), run: function () { applyFilter('All'); go(p.id)(); } };
  }), PROJECTS.map(function (p) {
    return { label: 'Open the ' + p.title + ' demo', hint: 'live demo', keywords: p.tags.join(' '), run: function () { window.location.href = p.demo; } };
  }), [
    { label: 'Switch theme', hint: 'command', keywords: 'dark light mode', run: toggleTheme },
    { label: 'Copy my email address', hint: 'command', keywords: 'contact mail', run: function () {
        if (navigator.clipboard) navigator.clipboard.writeText(PROFILE.email).catch(function () {});
        formStatus.dataset.kind = 'ok'; formStatus.textContent = 'Copied ' + PROFILE.email + '.'; } },
  ], ['GitHub', 'LinkedIn'].filter(linkUrl).map(function (name) {
    return { label: 'Open ' + name, hint: 'link', run: function () { window.location.href = linkUrl(name); } };
  }));
  var matches = [], active = 0, opener = null;
  function renderPalette() {
    var q = input.value.trim().toLowerCase();
    matches = COMMANDS.filter(function (c) { return !q || (c.label + ' ' + (c.keywords || '') + ' ' + c.hint).toLowerCase().indexOf(q) > -1; });
    active = Math.min(active, Math.max(matches.length - 1, 0));
    listEl.innerHTML = matches.map(function (c, i) {
      return '<li role="option" id="cmd-' + i + '" aria-selected="' + (i === active) + '">' + esc(c.label) + '<span>' + esc(c.hint) + '</span></li>';
    }).join('');
    $('paletteEmpty').hidden = matches.length > 0;
    if (matches.length) input.setAttribute('aria-activedescendant', 'cmd-' + active); else input.removeAttribute('aria-activedescendant');
    var sel = $('cmd-' + active);
    if (sel) sel.scrollIntoView({ block: 'nearest' });
  }
  function openPalette() {
    if (palette.open) return;
    opener = document.activeElement;
    input.value = ''; active = 0; renderPalette();
    palette.showModal(); input.focus();
  }
  function closePalette() { if (palette.open) palette.close(); }
  function run(i) { var c = matches[i]; if (!c) return; closePalette(); c.run(); }
  palette.addEventListener('close', function () { if (opener && opener.focus) opener.focus(); });
  $('paletteBtn').addEventListener('click', openPalette);
  input.addEventListener('input', function () { active = 0; renderPalette(); });
  input.addEventListener('keydown', function (e) {
    var n = Math.max(matches.length, 1);
    if (e.key === 'ArrowDown') { e.preventDefault(); active = (active + 1) % n; renderPalette(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); active = (active - 1 + n) % n; renderPalette(); }
    else if (e.key === 'Enter') { e.preventDefault(); run(active); }
  });
  listEl.addEventListener('click', function (e) { var li = e.target.closest('li'); if (li) run(+li.id.slice(4)); });
  palette.addEventListener('click', function (e) { if (e.target === palette) closePalette(); });   // a click on the backdrop
  document.addEventListener('keydown', function (e) {
    var typing = /^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName);
    if ((e.key === 'k' || e.key === 'K') && (e.ctrlKey || e.metaKey)) { e.preventDefault(); if (palette.open) closePalette(); else openPalette(); }
    else if (e.key === '/' && !typing && !palette.open) { e.preventDefault(); openPalette(); }
  });

  // ---- sections ease in as they reach the viewport; everything is simply shown when motion
  // is unwelcome or the browser can't watch for it
  var reveals = [].slice.call(document.querySelectorAll('.reveal'));
  function show(el) { el.classList.add('in'); }
  if (!('IntersectionObserver' in window) || reducedMotion) {
    reveals.forEach(show);
  } else {
    var watcher = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { show(e.target); watcher.unobserve(e.target); } });
    }, { rootMargin: '0px 0px -8% 0px' });
    reveals.forEach(function (el) { watcher.observe(el); });
  }

  // ---- the nav marks the section being read: the last one whose top has passed a line
  // a third of the way down, or the last section once the page can scroll no further.
  // The sections are the nav's own targets, so adding a link is the only change needed.
  var links = [].slice.call(document.querySelectorAll('.bar nav a'));
  var sections = links.map(function (a) { return $(a.getAttribute('href').slice(1)); });
  var READING_LINE = 1 / 3;
  // The last sections are too short to reach the reading line, so at the foot of the page the
  // one a visitor clicked stays marked while it's on screen; otherwise the last section is.
  var clicked = -1;
  links.forEach(function (a, i) { a.addEventListener('click', function () { clicked = i; }); });
  function onScreen(s) { var r = s.getBoundingClientRect(); return r.top < window.innerHeight && r.bottom > 0; }
  function markCurrent() {
    var current = -1;
    var atBottom = window.innerHeight + window.scrollY >= root.scrollHeight - 2;
    if (atBottom) current = clicked > -1 && onScreen(sections[clicked]) ? clicked : sections.length - 1;
    else sections.forEach(function (s, i) { if (s.getBoundingClientRect().top <= window.innerHeight * READING_LINE) current = i; });
    links.forEach(function (a, i) {
      if (i === current) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current');
    });
  }
  var queued = false;
  window.addEventListener('scroll', function () {
    if (queued) return;
    queued = true;
    requestAnimationFrame(function () { queued = false; markCurrent(); });
  }, { passive: true });
  window.addEventListener('resize', markCurrent);
  markCurrent();
})();
