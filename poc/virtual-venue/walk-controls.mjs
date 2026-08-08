import { Script } from 'playcanvas';

export class WalkControls extends Script {
  static scriptName = 'walkControls';

  initialize() {
    this.speed = 3.2;
    this.yaw = 0;
    this.pitch = 0;
    this.keys = new Set();
    this.canvas = this.app.graphicsDevice.canvas;

    this.onKeyDown = (event) => {
      if (['INPUT', 'TEXTAREA'].includes(event.target?.tagName)) return;
      this.keys.add(event.code);
    };
    this.onKeyUp = (event) => this.keys.delete(event.code);
    this.onCanvasClick = () => {
      if (document.pointerLockElement !== this.canvas) {
        this.canvas.requestPointerLock?.();
      }
    };
    this.onMouseMove = (event) => {
      if (document.pointerLockElement !== this.canvas) return;
      this.yaw -= event.movementX * 0.12;
      this.pitch = Math.max(-75, Math.min(75, this.pitch - event.movementY * 0.12));
    };

    window.addEventListener('keydown', this.onKeyDown);
    window.addEventListener('keyup', this.onKeyUp);
    this.canvas.addEventListener('click', this.onCanvasClick);
    document.addEventListener('mousemove', this.onMouseMove);

    this.on('destroy', () => {
      window.removeEventListener('keydown', this.onKeyDown);
      window.removeEventListener('keyup', this.onKeyUp);
      this.canvas.removeEventListener('click', this.onCanvasClick);
      document.removeEventListener('mousemove', this.onMouseMove);
    });
  }

  update(dt) {
    const position = this.entity.getPosition().clone();
    const yaw = (this.yaw * Math.PI) / 180;
    let forward = 0;
    let right = 0;

    if (this.keys.has('KeyW') || this.keys.has('ArrowUp')) forward += 1;
    if (this.keys.has('KeyS') || this.keys.has('ArrowDown')) forward -= 1;
    if (this.keys.has('KeyD') || this.keys.has('ArrowRight')) right += 1;
    if (this.keys.has('KeyA') || this.keys.has('ArrowLeft')) right -= 1;

    if (forward || right) {
      const length = Math.hypot(forward, right) || 1;
      forward /= length;
      right /= length;
      const step = this.speed * dt;

      position.x += (-Math.sin(yaw) * forward + Math.cos(yaw) * right) * step;
      position.z += (-Math.cos(yaw) * forward - Math.sin(yaw) * right) * step;
      position.x = Math.max(-6.6, Math.min(6.6, position.x));
      position.z = Math.max(-8.7, Math.min(8.2, position.z));
      position.y = 1.65;
      this.entity.setPosition(position);
    }

    this.entity.setEulerAngles(this.pitch, this.yaw, 0);
  }
}
