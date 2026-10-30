import {AbsoluteFill, CanvasImage, interpolate, staticFile, useCurrentFrame} from 'remotion';

export const Runway = () => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{background: '#0b1b23', alignItems: 'center', justifyContent: 'center'}}>
    <div style={{width: 1640, height: 922.5, borderRadius: 24, overflow: 'hidden', boxShadow: '0 35px 95px #0009',
      scale: interpolate(frame, [0, 227], [.96, 1.02])}}>
      <CanvasImage src={staticFile('app-airport-map.jpg')} style={{width: '100%', height: '100%'}} />
    </div>
  </AbsoluteFill>;
};
