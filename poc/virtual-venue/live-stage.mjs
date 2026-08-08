import {
  ADDRESS_CLAMP_TO_EDGE,
  Color,
  FILTER_LINEAR,
  PIXELFORMAT_R8_G8_B8,
  Script,
  StandardMaterial,
  Texture,
} from 'playcanvas';

export class LiveStage extends Script {
  static scriptName = 'liveStage';

  initialize() {
    this.video = document.createElement('video');
    this.video.autoplay = true;
    this.video.muted = true;
    this.video.playsInline = true;
    this.video.crossOrigin = 'anonymous';
    Object.assign(this.video.style, {
      width: '1px',
      height: '1px',
      position: 'absolute',
      opacity: '0',
      pointerEvents: 'none',
      zIndex: '-1000',
    });
    document.body.appendChild(this.video);

    this.texture = new Texture(this.app.graphicsDevice, {
      format: PIXELFORMAT_R8_G8_B8,
      minFilter: FILTER_LINEAR,
      magFilter: FILTER_LINEAR,
      addressU: ADDRESS_CLAMP_TO_EDGE,
      addressV: ADDRESS_CLAMP_TO_EDGE,
      mipmaps: false,
    });
    this.texture.setSource(this.video);

    this.material = new StandardMaterial();
    this.material.diffuse = new Color(0.02, 0.02, 0.025);
    this.material.emissive = new Color(0.08, 0.08, 0.1);
    this.material.useLighting = false;
    this.material.update();
    this.entity.render.material = this.material;

    this.setStream = async (stream) => {
      this.video.src = '';
      this.video.srcObject = stream;
      await this.video.play();
      this.attachTexture();
    };

    this.setUrl = async (url) => {
      this.video.srcObject = null;
      this.video.src = url;
      this.video.loop = true;
      this.video.load();
      await this.video.play();
      this.attachTexture();
    };

    this.app.on('ocn:set-stage-stream', this.setStream);
    this.app.on('ocn:set-stage-url', this.setUrl);

    this.on('destroy', () => {
      this.app.off('ocn:set-stage-stream', this.setStream);
      this.app.off('ocn:set-stage-url', this.setUrl);
      this.texture.destroy();
      this.material.destroy();
      const stream = this.video.srcObject;
      if (stream?.getTracks) stream.getTracks().forEach((track) => track.stop());
      this.video.remove();
    });
  }

  attachTexture() {
    this.material.diffuseMap = this.texture;
    this.material.emissiveMap = this.texture;
    this.material.emissive = new Color(1, 1, 1);
    this.material.update();
  }

  update() {
    if (this.video.readyState >= 2) this.texture.upload();
  }
}
