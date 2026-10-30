import {AbsoluteFill, CanvasImage, Easing, interpolate, staticFile, useCurrentFrame} from 'remotion';

export const Tower = () => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{background: '#0c1520', overflow: 'hidden'}}>
    <AbsoluteFill style={{transformOrigin: '66% 63%', scale: interpolate(frame, [0, 317], [1.02, 1.3], {easing: Easing.inOut(Easing.cubic)})}}>
      <CanvasImage src={staticFile('tower.png')} style={{width: 1920, height: 1080, objectFit: 'cover'}} />
      {/* Project all four capture corners into the photographed monitor, preserving its data labels. */}
      <div style={{position: 'absolute', left: 832.54, top: 494.67, width: 771, height: 440, transformOrigin: '0 0', transform: 'matrix3d(0.9932110911,0.001365437097,0,-0.0001073165761,-0.02870813397,0.8402647584,0,-0.00003382949932,0,0,1,0,12.63157895,0,0,1)', background: '#14252a'}}>
        <CanvasImage src={staticFile('app-airport-map.jpg')} style={{width: '100%', height: '100%', objectFit: 'fill', opacity: .94}} />
        <AbsoluteFill style={{background: 'linear-gradient(130deg, rgba(240,245,255,.09), transparent 60%, rgba(0,0,0,.12))'}} />
      </div>
    </AbsoluteFill>
    <AbsoluteFill style={{background: 'linear-gradient(90deg, rgba(5,12,20,.15), transparent 55%)'}} />
  </AbsoluteFill>;
};
