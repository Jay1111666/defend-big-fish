// 可选的本地网页端到端检查，使用独立浏览器上下文，不接触玩家存档。
// 先 npm install --prefix build/browser-tools --no-save playwright。
const {chromium} = require('../build/browser-tools/node_modules/playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const context=await browser.newContext({viewport:{width:1280,height:900}});
 const page=await context.newPage();
 const logs=[];
 page.on('console',m=>logs.push(m.type()+': '+m.text()));
 page.on('pageerror',e=>logs.push('PAGEERROR: '+e.stack));
 const ready=async()=>{
  await page.waitForFunction(()=>window.gameReady || window.gameLoadError,null,{timeout:120000});
  const error=await page.evaluate(()=>window.gameLoadError);
  assert(!error,error);
  await page.waitForFunction(()=>document.getElementById('game-loader').hidden);
 };
 const click=async(x,y,touch=false)=>{
  const b=await page.locator('#canvas').boundingBox();
  const px=b.x+x*b.width/1280,py=b.y+y*b.height/800;
  if(touch) await page.touchscreen.tap(px,py); else await page.mouse.click(px,py);
  await page.waitForTimeout(250);
 };
 const save=()=>page.evaluate(()=>JSON.parse(localStorage.getItem('defend-big-fish.save.v1')));
 try{
  await page.goto('http://127.0.0.1:8000/'); await ready();
  await click(640,435); await click(966,55);
  await click(640,610);
  assert.equal((await save()).stars,300);
  await click(640,610);
  assert.equal((await save()).selected,'gpt');
  await click(978,610);
  assert.equal((await save()).stars,0);
  await click(978,610);
  assert.equal((await save()).selected,'claude');
  await page.screenshot({path:'build/web-shop.png'});
  await click(1117,133);
  await click(1200,55);
  await click(765,335);
  assert.equal((await save()).audio.music,false);
  await click(640,527);
  await page.reload(); await ready();
  const reloaded=await save();
  assert.equal(reloaded.selected,'claude'); assert.equal(reloaded.stars,0);assert.equal(reloaded.audio.music,false);
  await click(640,435);
  await click(96,224); await click(78,380);
  await page.screenshot({path:'build/web-build-tower.png'});
  await click(1175,692); // cancel selection
  await click(1140,755); // start wave
  await page.waitForTimeout(2500);
  await click(889,55); // pause
  await page.screenshot({path:'build/web-combat.png'});
  await click(1045,55);
  await click(800,515); // level ten
  await page.screenshot({path:'build/web-level-ten.png'});
  console.log('DESKTOP_BROWSER_OK: purchase, equip, settings, refresh persistence, build, wave, level ten');
  console.log('MEDIA',await page.evaluate(()=>({ume:window.MM?.UME,mmKeys:Object.keys(window.MM||{})})));
  const mobile=await browser.newContext({viewport:{width:844,height:390},isMobile:true,hasTouch:true,deviceScaleFactor:1});
  const mp=await mobile.newPage();
  await mp.goto('http://127.0.0.1:8000/');
  await mp.waitForFunction(()=>window.gameReady || window.gameLoadError,null,{timeout:120000});
  assert(!(await mp.evaluate(()=>window.gameLoadError)));
  await mp.waitForFunction(()=>document.getElementById('game-loader').hidden);
  const tap=async(x,y)=>{const b=await mp.locator('#canvas').boundingBox(); await mp.touchscreen.tap(b.x+x*b.width/1280,b.y+y*b.height/800);await mp.waitForTimeout(250);};
  await tap(640,435);await tap(966,55);await tap(640,610);
  const mobileSave=await mp.evaluate(()=>JSON.parse(localStorage.getItem('defend-big-fish.save.v1')));
  assert.equal(mobileSave.stars,300);
  await mp.screenshot({path:'build/web-mobile.png'});
  console.log('MOBILE_TOUCH_OK: scaled canvas touch buys exactly one character');
 }catch(e){await page.screenshot({path:'build/web-play-error.png'});console.error(e.stack);process.exitCode=1;}
 finally{fs.writeFileSync('build/web-play.log',logs.join('\n'));await browser.close();}
})();
