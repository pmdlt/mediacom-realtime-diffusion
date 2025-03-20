import * as piexif from 'piexifjs';

interface IImageInfo {
  prompt?: string;
  negative_prompt?: string;
  seed?: number;
  guidance_scale?: number;
}
export enum windowType {
  image = 'image',
  video = 'video'
}

export function snapImage(imageEl: HTMLImageElement, info: IImageInfo) {
  try {
    const zeroth: { [key: string]: any } = {};
    const exif: { [key: string]: any } = {};
    const gps: { [key: string]: any } = {};
    zeroth[piexif.ImageIFD.Make] = 'LCM Image-to-Image ControNet';
    zeroth[piexif.ImageIFD.ImageDescription] =
      `prompt: ${info?.prompt} | negative_prompt: ${info?.negative_prompt} | seed: ${info?.seed} | guidance_scale: ${info?.guidance_scale}`;
    zeroth[piexif.ImageIFD.Software] =
      'https://github.com/radames/Real-Time-Latent-Consistency-Model';
    exif[piexif.ExifIFD.DateTimeOriginal] = new Date().toISOString();

    const exifObj = { '0th': zeroth, Exif: exif, GPS: gps };
    const exifBytes = piexif.dump(exifObj);

    const canvas = document.createElement('canvas');
    canvas.width = imageEl.naturalWidth;
    canvas.height = imageEl.naturalHeight;
    const ctx = canvas.getContext('2d') as CanvasRenderingContext2D;
    ctx.drawImage(imageEl, 0, 0);
    const dataURL = canvas.toDataURL('image/jpeg');
    const withExif = piexif.insert(exifBytes, dataURL);

    const a = document.createElement('a');
    a.href = withExif;
    a.download = `lcm_txt_2_img${Date.now()}.png`;
    a.click();
  } catch (err) {
    console.log(err);
  }
}

export function expandWindow(url: string): Window {
  const expandedWindow = window.open(
    '',
    '_blank',
    'toolbar=no,location=no,status=no,menubar=no,scrollbars=no,resizable=yes,width=800,height=600'
  );

  if (expandedWindow) {
    expandedWindow.document.write(`
    <html>
    <head>
    <title>Expanded View</title>
    <style>
    body {
      margin: 0;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
      background-color: black;
      position: relative;
    }
    img {
      width: 100%;
      height: 100%;
    }
    .epfl-logo {
      position: absolute;
      bottom: 15px;
      right: 15px;
      width: 20%;
      height: auto;
      opacity: 0.5;
    }
    .watermark {
      position: absolute;
      bottom: 10px;
      left: 10px;
      color: white;
      font-size: 30px;
      opacity: 0.7;
    }
    </style>
    </head>
    <body>
    <img src="${url}" alt="Expanded Image">
    <img src="/epfl-logo.svg" alt="EPFL Logo" class="epfl-logo">
    <div class="watermark">AI Generated Content, Osaka 2025</div>
    <script>
      document.documentElement.requestFullscreen().catch(console.error);
    </script>
    </body>
    </html>
    `);
  }

  return expandedWindow;
}