import {AbsoluteFill, CanvasImage, Easing, interpolate, staticFile, useCurrentFrame} from 'remotion';

export const Product = () => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{background: 'radial-gradient(ellipse at 65% 30%, #294249 0%, #10232d 50%, #081620 100%)', perspective: 2200}}>
    <div style={{position: 'absolute', left: 130, top: 105, width: 780, height: 833, borderRadius: 26, overflow: 'hidden', boxShadow: '0 45px 100px #0008', transform: 'rotateY(5deg)',
      translate: interpolate(frame, [0, 70, 347], ['0px 60px', '0px 0px', '0px -12px'], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)}),
      opacity: interpolate(frame, [0, 35], [0, 1], {extrapolateRight: 'clamp'})}}>
      <CanvasImage src={staticFile('app-dashboard.jpg')} style={{width: '100%', height: '100%'}} />
    </div>
    <div style={{position: 'absolute', left: 1100, top: 105, width: 620, height: 830, borderRadius: 24, overflow: 'hidden', border: '1px solid #ffffff30', boxShadow: '0 45px 100px #0008', transform: 'rotateY(-5deg)',
      translate: interpolate(frame, [30, 110, 347], ['80px 35px', '0px 0px', '-15px -8px'], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)}),
      opacity: interpolate(frame, [30, 80], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
      <CanvasImage src={staticFile('app-forecast-chart.jpg')} style={{width: '100%', height: '100%'}} />
    </div>
  </AbsoluteFill>;
};
