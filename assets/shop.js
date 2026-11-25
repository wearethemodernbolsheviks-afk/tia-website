/* TIA Supply Depot: filters, size picker, cart, Fourthwall checkout.
   Store settings live in /shop/fourthwall.json. The cart is kept in this browser only. */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var KEY = 'tia-cart-v1';
  var SIZES = { tee: ['S', 'M', 'L', 'XL', '2XL', '3XL', '4XL'], cap: ['One size'], print: ['A3'], digital: ['Digital'] };
  var PRICE = { tee: { _: 35 }, cap: { _: 20 }, print: { A3: 18 }, digital: { _: 9 } };
  var LABEL = { tee: 'TEE', cap: 'CAP', print: 'PRINT', digital: 'DIGITAL' };

  function money(n) { return '$' + (Math.round(n * 100) % 100 ? n.toFixed(2) : n.toFixed(0)); }
  function price(p, size) {
    if (p.prices && p.prices[size] != null) return p.prices[size];
    var t = PRICE[p.type]; return t[size] != null ? t[size] : t._;
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  /* ---------- products, read from the page ---------- */
  var products = {};
  $$('.prod').forEach(function (el) {
    var pid = $('.pid', el), id = pid ? pid.textContent.trim() : '';
    var type, sku, m;
    if (el.getAttribute('data-sku')) {
      sku = el.getAttribute('data-sku'); type = el.getAttribute('data-type');
    } else if ((m = id.match(/^ITEM (\d+)$/))) {
      var n = parseInt(m[1], 10);
      type = n <= 9 ? 'tee' : 'cap';
      sku = n <= 9 ? 'tee-' + m[1] : 'cap';
    } else if ((m = id.match(/^PRT (\d+)$/))) {
      type = 'print'; sku = 'print-' + m[1];
    } else {
      type = 'digital'; sku = 'full-wall';
    }
    var img = $('img', el);
    var prices = null;
    try { prices = JSON.parse(el.getAttribute('data-prices') || 'null'); } catch (e) { prices = null; }
    var p = { sku: sku, type: type, name: $('.nm', el).textContent.trim(), img: img ? img.getAttribute('src') : '', el: el, prices: prices };
    products[sku] = p;
    el.setAttribute('data-type', type);
    el.setAttribute('data-sku', sku);
    var btn = $('.add', el);
    if (!btn) return;
    var sizes = SIZES[type];
    if (sizes.length === 1) {
      btn.addEventListener('click', function () { add(sku, sizes[0], btn); });
      return;
    }
    var row = document.createElement('div');
    row.className = 'sizes';
    row.hidden = true;
    row.setAttribute('role', 'group');
    row.setAttribute('aria-label', 'Choose a size for ' + p.name);
    row.innerHTML = sizes.map(function (s) {
      return '<button type="button" class="sz mn" data-size="' + s + '">' + s + (type === 'print' || p.prices ? ' · ' + money(price(p, s)) : '') + '</button>';
    }).join('');
    btn.parentNode.insertBefore(row, btn.nextSibling);
    btn.setAttribute('aria-expanded', 'false');
    btn.addEventListener('click', function () {
      var open = row.hidden;
      row.hidden = !open;
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      btn.textContent = open ? 'Close' : 'Choose size';
      if (open) { var f = $('.sz', row); if (f) f.focus(); }
    });
    row.addEventListener('click', function (e) {
      var b = e.target.closest('.sz');
      if (!b) return;
      add(sku, b.getAttribute('data-size'), b);
      row.hidden = true;
      btn.setAttribute('aria-expanded', 'false');
      btn.textContent = 'Choose size';
      btn.focus();
    });
  });

  /* ---------- filters ---------- */
  var chips = $$('.chip[data-f]');
  chips.forEach(function (c) {
    c.addEventListener('click', function () {
      var f = c.getAttribute('data-f');
      chips.forEach(function (x) { var on = x === c; x.classList.toggle('on', on); x.setAttribute('aria-pressed', on ? 'true' : 'false'); });
      $$('.prod').forEach(function (el) { el.hidden = !(f === 'all' || el.getAttribute('data-type') === f); });
      $$('.shop-grp').forEach(function (g) { g.hidden = !$('.prod:not([hidden])', g); });
    });
  });

  /* ---------- cart state ---------- */
  var cart = [];
  try { cart = JSON.parse(localStorage.getItem(KEY) || '[]').filter(function (l) { return products[l.sku] && SIZES[products[l.sku].type].indexOf(l.size) >= 0; }); } catch (e) { cart = []; }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(cart)); } catch (e) {} }
  function count() { return cart.reduce(function (n, l) { return n + l.qty; }, 0); }
  function total() { return cart.reduce(function (n, l) { return n + l.qty * price(products[l.sku], l.size); }, 0); }

  function add(sku, size, fromBtn) {
    var line = cart.filter(function (l) { return l.sku === sku && l.size === size; })[0];
    if (line) line.qty = Math.min(line.qty + 1, 20); else cart.push({ sku: sku, size: size, qty: 1 });
    save(); render();
    if (fromBtn) {
      var b = $('.add', products[sku].el), old = b.textContent;
      b.textContent = 'Added ✓';
      b.classList.add('ok');
      setTimeout(function () { b.classList.remove('ok'); b.textContent = SIZES[products[sku].type].length === 1 ? 'Add to cart' : 'Choose size'; }, 1400);
    }
    toast(products[sku].name + (size !== 'One size' && size !== 'Digital' ? ' · ' + size : '') + ' added');
  }

  /* ---------- drawer ---------- */
  var ov = document.createElement('div');
  ov.className = 'cart-ov';
  ov.hidden = true;
  var dr = document.createElement('aside');
  dr.className = 'cart-dr';
  dr.hidden = true;
  dr.setAttribute('role', 'dialog');
  dr.setAttribute('aria-modal', 'true');
  dr.setAttribute('aria-label', 'Cart');
  dr.innerHTML =
    '<div class="cart-h mn"><span>CART · <b id="cart-n">0</b></span><button type="button" class="cart-x" aria-label="Close cart">×</button></div>' +
    '<ul class="cart-l" id="cart-l"></ul>' +
    '<div class="cart-f"><div class="cart-t mn"><span>SUBTOTAL</span><b id="cart-total">$0</b></div>' +
    '<p class="cart-note">Prices in US dollars. Shipping, tax and your final total are shown at checkout.</p>' +
    '<button type="button" class="cart-go" id="cart-go">Checkout</button>' +
    '<p class="cart-msg" id="cart-msg" role="status"></p></div>';
  var tst = document.createElement('div');
  tst.className = 'cart-toast mn';
  tst.setAttribute('role', 'status');
  document.body.appendChild(ov);
  document.body.appendChild(dr);
  document.body.appendChild(tst);

  var lastFocus = null;
  function openCart() {
    lastFocus = document.activeElement;
    ov.hidden = false; dr.hidden = false;
    requestAnimationFrame(function () { dr.classList.add('in'); ov.classList.add('in'); });
    $('.cart-x', dr).focus();
    document.documentElement.style.overflow = 'hidden';
  }
  function closeCart() {
    dr.classList.remove('in'); ov.classList.remove('in');
    setTimeout(function () { dr.hidden = true; ov.hidden = true; }, 220);
    document.documentElement.style.overflow = '';
    if (lastFocus) lastFocus.focus();
  }
  ov.addEventListener('click', closeCart);
  $('.cart-x', dr).addEventListener('click', closeCart);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !dr.hidden) closeCart(); });

  var cartBtn = $('#cart-btn');
  if (cartBtn) cartBtn.addEventListener('click', function (e) { e.preventDefault(); openCart(); });

  var tt;
  function toast(msg) {
    tst.innerHTML = esc(msg) + ' <button type="button">VIEW CART</button>';
    tst.classList.add('in');
    $('button', tst).onclick = function () { tst.classList.remove('in'); openCart(); };
    clearTimeout(tt);
    tt = setTimeout(function () { tst.classList.remove('in'); }, 3200);
  }

  function render() {
    var n = count();
    if (cartBtn) { var lab = $('.cart-count', cartBtn); if (lab) lab.textContent = n; }
    $('#cart-n').textContent = n;
    $('#cart-total').textContent = money(total());
    var list = $('#cart-l');
    if (!cart.length) {
      list.innerHTML = '<li class="cart-empty">Nothing here yet. Pick a tee, the cap or a print.</li>';
    } else {
      list.innerHTML = cart.map(function (l, i) {
        var p = products[l.sku];
        var sz = l.size === 'One size' || l.size === 'Digital' ? LABEL[p.type] : LABEL[p.type] + ' · ' + l.size;
        return '<li><img src="' + esc(p.img) + '" alt=""><div class="ci"><span class="cn">' + esc(p.name) + '</span><span class="cs mn">' + esc(sz) + ' · ' + money(price(p, l.size)) + '</span>' +
          '<div class="cq mn"><button type="button" data-i="' + i + '" data-d="-1" aria-label="One fewer">−</button><span aria-label="Quantity">' + l.qty + '</span><button type="button" data-i="' + i + '" data-d="1" aria-label="One more">+</button>' +
          '<button type="button" class="rm" data-i="' + i + '" data-d="0">REMOVE</button></div></div><b class="mn">' + money(l.qty * price(p, l.size)) + '</b></li>';
      }).join('');
    }
    $('#cart-go').disabled = !cart.length;
    $('#cart-msg').textContent = '';
  }
  $('#cart-l').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-i]');
    if (!b) return;
    var i = +b.getAttribute('data-i'), d = +b.getAttribute('data-d');
    if (d === 0) cart.splice(i, 1);
    else { cart[i].qty += d; if (cart[i].qty < 1) cart.splice(i, 1); if (cart[i] && cart[i].qty > 20) cart[i].qty = 20; }
    save(); render();
  });

  /* ---------- checkout ---------- */
  var config = null;
  function getConfig() {
    if (config) return Promise.resolve(config);
    return fetch('/shop/fourthwall.json', { cache: 'no-cache' }).then(function (r) { return r.json(); }).then(function (c) { config = c; return c; });
  }
  var API = 'https://storefront-api.fourthwall.com/v1/';
  function pickVariant(prod, size, strict) {
    var vs = (prod && (prod.variants || (prod.product && prod.product.variants))) || [];
    if (vs.length === 1 && !strict) return vs[0].id;
    var want = size.toLowerCase();
    var hit = vs.filter(function (v) {
      var a = v.attributes || {};
      var cand = [a.size && a.size.name, a.description, v.name].filter(Boolean).map(function (s) { return String(s).toLowerCase(); });
      return cand.some(function (c) { return c === want || c.split(/[\s,\/|-]+/).indexOf(want) !== -1; });
    })[0];
    return hit ? hit.id : '';
  }
  function lookupVariant(cfg, entry, size) {
    if (!cfg.storefrontToken || !entry || !entry.slug) return Promise.resolve('');
    var url = API + 'products/' + encodeURIComponent(entry.slug) + '?storefront_token=' + encodeURIComponent(cfg.storefrontToken);
    return fetch(url).then(function (r) { return r.json(); }).then(function (prod) { return pickVariant(prod, size); }).catch(function () { return ''; });
  }
  /* Every product in the Fourthwall shop, keyed by name, so items need no IDs: a product
     named exactly as on this page is found by itself. */
  function norm(s) { return String(s || '').toLowerCase().replace(/[‘’]/g, "'").replace(/[^a-z0-9']+/g, ' ').trim(); }
  var catalog = null;
  function getCatalog(cfg) {
    if (catalog) return catalog;
    if (!cfg.shop || !cfg.storefrontToken) return (catalog = Promise.resolve({}));
    var byName = {};
    function page(n, left) {
      var url = API + 'collections/all/products?storefront_token=' + encodeURIComponent(cfg.storefrontToken) + '&size=100' + (n == null ? '' : '&page=' + n);
      return fetch(url).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }).then(function (d) {
        (d.results || []).forEach(function (p) {
          if (p && p.name && (!p.access || p.access.type === 'PUBLIC' || p.access.type === 'HIDDEN')) (byName[norm(p.name)] = byName[norm(p.name)] || []).push(p);
        });
        var pg = d.paging || {};
        return pg.hasNextPage && left > 0 ? page((pg.pageNumber || 0) + 1, left - 1) : byName;
      });
    }
    catalog = page(null, 20).catch(function () { catalog = null; return null; });
    return catalog;
  }
  function hasIds(entry) { return !!(entry && entry.variants && Object.keys(entry.variants).some(function (k) { return entry.variants[k]; })); }
  function storeOpen(cfg, cat) {
    return !!cfg.shop && (cfg.live === true || !!(cat && Object.keys(cat).length) ||
      Object.keys(cfg.products || {}).some(function (k) { return hasIds(cfg.products[k]); }));
  }
  /* A print may be called "Lenin Moon" or "Lenin Moon Print" in Fourthwall; a tee only matches a
     product that has its size, so the tee and the print of the same name never get mixed up. */
  var SUFFIX = { tee: [' tee', ' t shirt', ' tshirt', ' shirt', ''], print: [' print', ' poster', ' a3 print', ''], cap: [''], digital: [''] };
  function findVariant(cat, p, size) {
    var keys = (SUFFIX[p.type] || ['']).map(function (s) { return norm(p.name + s); });
    for (var k = 0; k < keys.length; k++) {
      var list = (cat && cat[keys[k]]) || [];
      for (var j = 0; j < list.length; j++) {
        var id = pickVariant(list[j], size, p.type === 'tee');
        if (id) return id;
      }
    }
    return '';
  }
  $('#cart-go').addEventListener('click', function () {
    var msg = $('#cart-msg'), go = $('#cart-go');
    if (!cart.length) return;
    go.disabled = true;
    msg.textContent = 'Connecting to the store…';
    getConfig().then(function (cfg) {
      return Promise.resolve(getCatalog(cfg)).then(function (cat) { return [cfg, cat]; });
    }).then(function (cc) {
      var cfg = cc[0], cat = cc[1];
      if (cfg.shop && cat === null) throw new Error('store unreachable');
      if (!storeOpen(cfg, cat)) {
        msg.innerHTML = 'The store is opening soon. Your cart is saved on this device, so you can check out the moment it goes live. New drops are announced on <a href="https://www.youtube.com/@Invariance_Tech" target="_blank" rel="noopener">YouTube</a>.';
        go.disabled = false;
        return;
      }
      return Promise.all(cart.map(function (l) {
        var entry = (cfg.products || {})[l.sku] || {};
        var id = entry.variants && entry.variants[l.size];
        if (id) return Promise.resolve(id);
        if (entry.slug) return lookupVariant(cfg, entry, l.size);
        return Promise.resolve(findVariant(cat, products[l.sku], l.size));
      })).then(function (ids) {
        var missing = cart.filter(function (l, i) { return !ids[i]; });
        if (missing.length) {
          msg.textContent = 'Not in the store yet: ' + missing.map(function (l) { return products[l.sku].name + (SIZES[products[l.sku].type].length > 1 ? ' (' + l.size + ')' : ''); }).join(', ') + '. Remove it to check out the rest.';
          go.disabled = false;
          return;
        }
        var items = cart.map(function (l, i) { return ids[i] + ':' + l.qty; }).join(',');
        var domain = cfg.shop.replace(/^https?:\/\//, '').replace(/\/+$/, '');
        msg.textContent = 'Opening secure checkout…';
        location.href = 'https://' + domain + '/cart/checkout?products=' + encodeURIComponent(items).replace(/%3A/g, ':').replace(/%2C/g, ',') + '&currency=' + encodeURIComponent(cfg.currency || 'USD');
      });
    }).catch(function () {
      msg.textContent = 'Could not reach the store. Check your connection and try again.';
      go.disabled = false;
    });
  });

  /* store status line */
  getConfig().then(function (cfg) {
    return Promise.resolve(getCatalog(cfg)).then(function (cat) {
      var st = $('#shop-status');
      if (!storeOpen(cfg, cat)) return;
      if (st) { st.innerHTML = '<span class="dot"></span>DROP 01 · LIVE'; st.style.color = '#39D98A'; }
      /* once the store is open, items not yet in it can't be bought: say so on the card */
      Object.keys(products).forEach(function (sku) {
        var p = products[sku], entry = (cfg.products || {})[sku];
        var ok = hasIds(entry) || !!(entry && entry.slug && cfg.storefrontToken) ||
          SIZES[p.type].some(function (sz) { return !!findVariant(cat, p, sz); });
        if (ok) return;
        var b = $('.add', p.el);
        if (b) { b.disabled = true; b.textContent = 'Coming soon'; b.classList.add('soon'); }
        var row = $('.sizes', p.el);
        if (row) row.hidden = true;
      });
    });
  }).catch(function () {});

  render();
})();
