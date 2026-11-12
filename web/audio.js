/* Background music runs on the browser audio thread, independently of pygame frames. */
(() => {
  class GameMusic {
    constructor(url) {
      this.url = url;
      this.context = null;
      this.bufferPromise = null;
      this.source = null;
      this.gain = null;
      this.enabled = false;
      this.error = '';
      // AudioContext.resume must originate in a user gesture on mobile Safari.
      const unlock = () => {
        this.unlock().catch(error => this.report(error));
      };
      document.addEventListener('pointerdown', unlock, {capture: true, passive: true});
      document.addEventListener('keydown', unlock, {capture: true});
      window.addEventListener('pagehide', () => this.stop());
    }

    report(error) {
      this.error = String(error);
      console.warn('Background music:', this.error);
    }

    async unlock() {
      if (!this.context) {
        const Context = window.AudioContext || window.webkitAudioContext;
        if (!Context) throw new Error('Web Audio is unavailable');
        this.context = new Context({latencyHint: 'playback'});
      }
      if (this.context.state === 'suspended') await this.context.resume();
      if (this.enabled) await this.start();
    }

    async load() {
      if (!this.bufferPromise) {
        this.bufferPromise = (async () => {
          const response = await fetch(this.url);
          if (!response.ok) throw new Error(`Music HTTP ${response.status}`);
          const buffer = await this.context.decodeAudioData(await response.arrayBuffer());
          // Bring the small source-file boundary offset to zero without changing duration.
          const edge = Math.min(128, Math.floor(buffer.length / 4));
          for (let channel = 0; channel < buffer.numberOfChannels; channel++) {
            const samples = buffer.getChannelData(channel);
            for (let i = 0; i < edge; i++) {
              samples[i] *= i / edge;
              samples[samples.length - 1 - i] *= i / edge;
            }
          }
          return buffer;
        })().catch(error => {
          this.bufferPromise = null;
          throw error;
        });
      }
      return this.bufferPromise;
    }

    async start() {
      if (!this.context || !this.enabled || this.source) return;
      const buffer = await this.load();
      // A setting change while decoding must not start unwanted music or extra loops.
      if (!this.enabled || this.source) return;
      const source = this.context.createBufferSource();
      const gain = this.context.createGain();
      source.buffer = buffer;
      source.loop = true;
      source.connect(gain);
      gain.connect(this.context.destination);
      gain.gain.setValueAtTime(0, this.context.currentTime);
      gain.gain.linearRampToValueAtTime(0.42, this.context.currentTime + 0.04);
      source.onended = () => { source.disconnect(); gain.disconnect(); };
      this.source = source;
      this.gain = gain;
      this.error = '';
      source.start();
    }

    stop() {
      if (!this.source) return;
      const now = this.context.currentTime;
      this.gain.gain.cancelScheduledValues(now);
      this.gain.gain.setValueAtTime(this.gain.gain.value, now);
      this.gain.gain.linearRampToValueAtTime(0, now + 0.04);
      this.source.stop(now + 0.04);
      this.source = this.gain = null;
    }

    setEnabled(enabled) {
      this.enabled = Boolean(enabled);
      if (!this.enabled) this.stop();
      else if (this.context) this.start().catch(error => this.report(error));
    }
  }
  // PCM WAV is decoded natively by desktop and mobile browsers, including Safari.
  window.gameMusic = new GameMusic(new URL('audio/garden-loop.wav', document.baseURI).href);
})();
