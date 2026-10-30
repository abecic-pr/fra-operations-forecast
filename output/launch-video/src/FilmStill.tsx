import { AbsoluteFill, CanvasImage, interpolate, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';

export const FilmStill = ({src, from, to, origin = '50% 50%'}: {src: string; from: number; to: number; origin?: string}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  return <AbsoluteFill style={{overflow: 'hidden', background: '#0c1520'}}>
    <CanvasImage src={staticFile(src)} style={{width: 1920, height: 1080, objectFit: 'cover', transformOrigin: origin,
      scale: interpolate(frame, [0, durationInFrames - 1], [from, to], {extrapolateRight: 'clamp'})}} />
    <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 45%, transparent 45%, rgba(5,12,20,.24) 100%)'}} />
  </AbsoluteFill>;
};
