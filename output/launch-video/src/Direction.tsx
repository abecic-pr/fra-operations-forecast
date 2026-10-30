import {AbsoluteFill, CanvasImage, interpolate, staticFile, useCurrentFrame} from 'remotion';

export const Direction = () => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 40%, #dbe5e9, #b8c7d0)', alignItems: 'center', justifyContent: 'center', perspective: 2400}}>
    <div style={{width: 1620, height: 852, borderRadius: 36, overflow: 'hidden', boxShadow: '0 40px 95px #26374240',
      scale: interpolate(frame, [0, 167], [.98, 1.02]), transform: 'rotateX(2deg)'}}>
      <CanvasImage src={staticFile('app-direction.jpg')} style={{width: '100%', height: '100%'}} />
    </div>
  </AbsoluteFill>;
};
