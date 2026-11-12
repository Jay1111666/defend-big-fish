// Optional browser audio regression: npm install --prefix build/browser-tools --no-save playwright
const {chromium} = require('../build/browser-tools/node_modules/playwright');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({channel:'msedge', headless:true});
  const page = await browser.newPage({viewport:{width:1280,height:900}});
  const base = process.env.GAME_URL || 'http://127.0.0.1:8000/';
  let release;
  const gate = new Promise(resolve => release = resolve);
  await page.route('**/audio/garden-loop.wav', async route => {await gate; await route.continue();});
  try {
    await page.goto(base);
    await page.waitForFunction(()=>window.gameReady || window.gameLoadError,null,{timeout:120000});
    assert(!(await page.evaluate(()=>window.gameLoadError)));
    await page.waitForFunction(()=>document.getElementById('game-loader').hidden);
    const box = await page.locator('#canvas').boundingBox();
    await page.mouse.click(box.x + box.width/2, box.y + 435*box.height/800);
    await page.waitForFunction(()=>window.gameMusic.bufferPromise !== null);
    await page.evaluate(()=>window.gameMusic.setEnabled(false));
    release();
    await page.evaluate(async()=>{await window.gameMusic.bufferPromise;});
    assert.equal(await page.evaluate(()=>window.gameMusic.source),null,'Disabling during decode must prevent late playback');
    await page.evaluate(()=>{
      const music=window.gameMusic;
      window.musicSourcesCreated=0;
      const create=music.context.createBufferSource.bind(music.context);
      music.context.createBufferSource=()=>{window.musicSourcesCreated++;return create();};
      music.setEnabled(true);music.setEnabled(true);
    });
    await page.waitForFunction(()=>Boolean(window.gameMusic.source));
    assert.equal(await page.evaluate(()=>window.musicSourcesCreated),1,'Repeated enable must not layer music');
    const state=await page.evaluate(async()=>{
      const music=window.gameMusic, context=music.context;
      const buffer=await music.bufferPromise;
      const edgeMax=Math.max(...Array.from({length:buffer.numberOfChannels},(_,c)=>{
        const samples=buffer.getChannelData(c);return Math.abs(samples[0])+Math.abs(samples[samples.length-1]);
      }));
      const code=`class Meter extends AudioWorkletProcessor {
        process(inputs, outputs) {
          const input=inputs[0], output=outputs[0];let peak=0,sum=0;
          for(let c=0;c<output.length;c++) {if(input[c]) output[c].set(input[c]);}
          if(input[0]) {for(const s of input[0]){peak=Math.max(peak,Math.abs(s));sum+=s*s;}
            this.port.postMessage({frame:currentFrame,peak,rms:Math.sqrt(sum/input[0].length)});}
          return true;
        }
      } registerProcessor('music-meter',Meter);`;
      const url=URL.createObjectURL(new Blob([code],{type:'application/javascript'}));
      await context.audioWorklet.addModule(url);URL.revokeObjectURL(url);
      const meter=new AudioWorkletNode(context,'music-meter');
      window.musicBlocks=[];meter.port.onmessage=e=>window.musicBlocks.push(e.data);
      music.gain.disconnect();music.gain.connect(meter);meter.connect(context.destination);
      return {state:context.state,sampleRate:context.sampleRate,loop:music.source.loop,edgeMax};
    });
    assert.equal(state.state,'running');assert.equal(state.loop,true);assert.equal(state.edgeMax,0);
    await page.waitForTimeout(1000);
    // Simulate an expensive game frame; AudioWorklet keeps collecting on its audio thread.
    await page.evaluate(()=>{const end=performance.now()+650;while(performance.now()<end) {Math.sqrt(Math.random());}});
    await page.waitForTimeout(1000);
    const measured=await page.evaluate(()=>({
      blocks:window.musicBlocks.length,
      peak:Math.max(...window.musicBlocks.map(b=>b.peak)),
      silentBlocks:window.musicBlocks.filter(b=>b.peak<1e-7).length,
      frameJumps:window.musicBlocks.slice(1).map((b,i)=>b.frame-window.musicBlocks[i].frame).filter(delta=>delta!==128),
      error:window.gameMusic.error
    }));
    console.log('AUDIO_MEASUREMENTS',JSON.stringify(measured));
    assert(measured.blocks>300);assert(measured.peak>0.001 && measured.peak<0.99);
    assert.equal(measured.silentBlocks,0);assert.equal(measured.error,'');
    await page.evaluate(()=>window.gameMusic.setEnabled(false));
    assert.equal(await page.evaluate(()=>window.gameMusic.source),null);
    console.log('BROWSER_AUDIO_OK',JSON.stringify({base,...state,...measured}));
  } catch(error) {console.error(error.stack);process.exitCode=1;}
  finally {release();await browser.close();}
})();
