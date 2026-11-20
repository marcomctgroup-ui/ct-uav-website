/* v09 r01 Batch 3 (10 Nov 2026). CT Ency microphone icon button: EN/VI accessible name follows the voice state (data-voice-state) and the page language. */
(() => {
 const button = document.getElementById('cuMicrophone');
 if (!button) return;
 const labels = {
  idle: {en: 'Voice input', vi: 'Nhập bằng giọng nói'},
  recording: {en: 'Stop microphone', vi: 'Dừng ghi âm'},
  converting: {en: 'Converting speech to text', vi: 'Đang chuyển giọng nói thành văn bản'}
 };
 const sync = () => {
  const set = labels[button.dataset.voiceState] || labels.idle;
  const text = document.documentElement.lang === 'vi' ? set.vi : set.en;
  if (button.getAttribute('aria-label') !== text) button.setAttribute('aria-label', text);
  if (button.title !== text) button.title = text;
 };
 new MutationObserver(sync).observe(button, {attributes: true, attributeFilter: ['data-voice-state']});
 new MutationObserver(sync).observe(document.documentElement, {attributes: true, attributeFilter: ['lang']});
 sync();
})();
