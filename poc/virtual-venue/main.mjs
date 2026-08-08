import { Vec3 } from 'playcanvas';
import { whenReady } from '@playcanvas/web-components';

const seatPositions = {
  'front-left': [-3, 1.65, -1.4],
  'front-center': [0, 1.65, -1.2],
  'front-right': [3, 1.65, -1.4],
  balcony: [0, 3.9, 6.5],
};

const { app } = await whenReady('pc-app');
const cameraElement = await whenReady('#camera');
const camera = cameraElement.entity;
const status = document.querySelector('#stage-status');
const cameraButton = document.querySelector('#camera-button');
const videoFile = document.querySelector('#video-file');
let activeStream = null;
let activeObjectUrl = null;

function focusStage() {
  camera.lookAt(new Vec3(0, 2.4, -9.5));
}

for (const button of document.querySelectorAll('[data-seat]')) {
  button.addEventListener('click', () => {
    const position = seatPositions[button.dataset.seat];
    if (!position) return;
    document.exitPointerLock?.();
    camera.setPosition(...position);
    focusStage();
    status.textContent = `${button.textContent} selected`;
  });
}

cameraButton.addEventListener('click', async () => {
  try {
    if (activeStream) {
      activeStream.getTracks().forEach((track) => track.stop());
      activeStream = null;
    }
    activeStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: true,
    });
    app.fire('ocn:set-stage-stream', activeStream);
    status.textContent = 'LIVE — local camera is playing on the virtual stage';
    cameraButton.textContent = 'Restart live camera';
  } catch (error) {
    status.textContent = `Camera unavailable: ${error?.message || 'permission denied'}`;
  }
});

videoFile.addEventListener('change', () => {
  const [file] = videoFile.files || [];
  if (!file) return;
  if (activeObjectUrl) URL.revokeObjectURL(activeObjectUrl);
  activeObjectUrl = URL.createObjectURL(file);
  app.fire('ocn:set-stage-url', activeObjectUrl);
  status.textContent = `${file.name} is playing on the virtual stage`;
});

const help = document.querySelector('#help');
document.querySelector('#help-button').addEventListener('click', () => {
  help.hidden = false;
});
document.querySelector('#help-close').addEventListener('click', () => {
  help.hidden = true;
});

window.addEventListener('beforeunload', () => {
  if (activeStream) activeStream.getTracks().forEach((track) => track.stop());
  if (activeObjectUrl) URL.revokeObjectURL(activeObjectUrl);
});
