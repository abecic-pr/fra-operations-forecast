import {AbsoluteFill, CanvasImage, interpolate, staticFile, useCurrentFrame} from 'remotion';

export const ArrivalForecast = () => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{background: '#10232d'}}>
    <CanvasImage src={staticFile('tower.png')} style={{width: 1920, height: 1080, objectFit: 'cover', filter: 'blur(12px) brightness(.38)', scale: 1.06}} />
    <div style={{position: 'absolute', left: 200, top: 140, width: 1520, height: 800, overflow: 'hidden', borderRadius: 32, boxShadow: '0 35px 120px #000a',
      scale: interpolate(frame, [0, 119], [.98, 1.015])}}>
      <CanvasImage src={staticFile('app-direction.jpg')} style={{width: '100%', height: '100%'}} />
    </div>
  </AbsoluteFill>;
};
