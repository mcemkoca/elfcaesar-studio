const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const ud = '/tmp/e2e/profile';
  fs.rmSync(ud, { recursive: true, force: true });
  fs.mkdirSync(ud + '/NativeMessagingHosts', { recursive: true });
  const host = JSON.parse(fs.readFileSync('/home/claude/v6110/browser-extension/com.dante.elfcaesar.json'));
  host.path = '/tmp/e2e/host.sh';
  for (const d of [ud + '/NativeMessagingHosts', process.env.HOME + '/.config/chromium/NativeMessagingHosts', process.env.HOME + '/.config/google-chrome-for-testing/NativeMessagingHosts']) {
    fs.mkdirSync(d, { recursive: true }); fs.writeFileSync(d + '/com.dante.elfcaesar.json', JSON.stringify(host));
  }
  const ext = '/home/claude/v6110/browser-extension';
  const ctx = await chromium.launchPersistentContext(ud, {
    channel: 'chromium', headless: true, ignoreHTTPSErrors: true, viewport: { width: 1100, height: 700 },
    env: { ...process.env, LOCALAPPDATA: '/tmp/e2e/lad' },
    args: [`--disable-extensions-except=${ext}`, `--load-extension=${ext}`,
      '--ignore-certificate-errors', '--no-proxy-server', '--host-resolver-rules=MAP www.elfmarket.com:443 127.0.0.1:8443, MAP www.elfmarket.com:80 127.0.0.1:8765, MAP elfmarket.com.giris-yap.xyz:80 127.0.0.1:8765'],
  });
  let [sw] = ctx.serviceWorkers();
  if (!sw) sw = await ctx.waitForEvent('serviceworker');
  const extId = sw.url().split('/')[2];
  console.log('extension id', extId);
  // eşleştir (popup betiği)
  const pop = await ctx.newPage();
  await pop.goto(`chrome-extension://${extId}/popup.html`);
  await pop.waitForTimeout(800);
  console.log('popup before:', await pop.locator('main').innerText());
  await pop.click('#pairBtn'); await pop.waitForTimeout(300); console.log('popup kod:', await pop.locator('#code').innerText());
  await pop.waitForTimeout(1500);
  console.log('popup after:', (await pop.locator('main').innerText()).split('\n').slice(0, 3).join(' | '));
  await pop.screenshot({ path: '/tmp/e2e/popup.png' });
  // gerçek site
  const page = await ctx.newPage();
  await page.goto('https://www.elfmarket.com/login.html');
  await page.waitForTimeout(1200);
  const btn = page.locator('elfcaesar-ui');
  console.log('ui host count', await btn.count());
  // kapalı shadow root: düğmeyi koordinatla tıkla (parola alanının sağ ucu)
  const box = await page.locator('#p').boundingBox();
  await page.mouse.click(box.x + box.width - 17, box.y + box.height / 2);
  await page.waitForTimeout(1200);
  await page.screenshot({ path: '/tmp/e2e/menu.png' });
  await page.mouse.click(box.x + box.width - 120, box.y + box.height + 6 + 30 + 18);
  await page.waitForTimeout(800);
  console.log('filled:', await page.inputValue('#u'), '/', await page.inputValue('#p'));
  await page.screenshot({ path: '/tmp/e2e/filled.png' });
  // http sürüm düşürme: aynı site şifresiz
  const dn = await ctx.newPage(); await dn.goto('http://www.elfmarket.com/login.html'); await dn.waitForTimeout(1200);
  const db = await dn.locator('#p').boundingBox(); await dn.mouse.click(db.x + db.width - 17, db.y + db.height / 2); await dn.waitForTimeout(1000);
  await dn.mouse.click(db.x + db.width - 120, db.y + db.height + 6 + 30 + 18); await dn.waitForTimeout(900);
  console.log('http filled:', JSON.stringify(await dn.inputValue('#p'))); await dn.screenshot({ path: '/tmp/e2e/downgrade.png' });
  // sahte site
  const ph = await ctx.newPage();
  await ph.goto('http://elfmarket.com.giris-yap.xyz/login.html');
  await ph.waitForTimeout(1500);
  await ph.screenshot({ path: '/tmp/e2e/phish.png' });
  const pb = await ph.locator('#p').boundingBox();
  await ph.mouse.click(pb.x + pb.width - 17, pb.y + pb.height / 2);
  await ph.waitForTimeout(1000);
  console.log('phish fields:', JSON.stringify(await ph.inputValue('#p')));
  await ph.screenshot({ path: '/tmp/e2e/phish_menu.png' });
  // ---- 6.11: kayıt formu — güçlü parola öner + gönderince kaydet
  const su = await ctx.newPage();
  await su.goto('https://www.elfmarket.com/signup.html'); await su.waitForTimeout(1200);
  const sb = await su.locator('#p1').boundingBox();
  await su.mouse.click(sb.x + sb.width - 17, sb.y + sb.height / 2); await su.waitForTimeout(1200);
  await su.screenshot({ path: '/tmp/e2e/gen_menu.png' });
  await su.mouse.click(sb.x + sb.width - 120, sb.y + sb.height + 6 + 30 + 18); await su.waitForTimeout(1500);
  const g1 = await su.inputValue('#p1'), g2 = await su.inputValue('#p2');
  console.log('generated:', g1.length, g1 === g2, /^[A-Za-z0-9_-]+$/.test(g1));
  await su.screenshot({ path: '/tmp/e2e/gen_filled.png' });
  await su.mouse.click(10, 10);
  await su.click('#go'); await su.waitForTimeout(4500);
  console.log('after submit url:', su.url());
  await su.screenshot({ path: '/tmp/e2e/save_banner.png' });
  // kapalı gölge kökü: banner sağ alt köşede; "Kaydet" düğmesini koordinatla tıkla
  const vp = su.viewportSize();
  await su.mouse.click(vp.width - 18 - 12 - 30, vp.height - 18 - 12 - 14); await su.waitForTimeout(1500);
  await su.screenshot({ path: '/tmp/e2e/saved.png' });
  // ---- değişen parola: login formunda farklı parola gönder → güncelle önerisi
  const lp = await ctx.newPage();
  await lp.goto('https://www.elfmarket.com/login.html'); await lp.waitForTimeout(1000);
  await lp.fill('#u', 'ayse@ornek.com'); await lp.fill('#p', 'Tamamen-Yeni-Parola-9');
  await lp.press('#p', 'Enter'); await lp.waitForTimeout(1500);
  await lp.screenshot({ path: '/tmp/e2e/update_banner.png' });
  await ctx.close();
})().catch((e) => { console.error('ERR', e); process.exit(1); });
