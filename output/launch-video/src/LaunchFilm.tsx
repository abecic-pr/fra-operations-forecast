import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {Cabin} from './Cabin';
import {Tower} from './Tower';
import {Product} from './Product';
import {Runway} from './Runway';
import {Direction} from './Direction';
import {Departure} from './Departure';
import {Approach} from './Approach';
import {ArrivalForecast} from './ArrivalForecast';
import {Arrival} from './Arrival';

export const LaunchFilm = () => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{background: '#07121d'}}>
    <TransitionSeries>
      <TransitionSeries.Sequence name="01 · From the cabin" durationInFrames={300}><Cabin /></TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 18})} />
      <TransitionSeries.Sequence name="02 · Inside the tower" durationInFrames={318}><Tower /></TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 18})} />
      <TransitionSeries.Sequence name="03 · Actual app and forecast" durationInFrames={348}><Product /></TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 18})} />
      <TransitionSeries.Sequence name="04 · Runway 18 outlook" durationInFrames={228}><Runway /></TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 18})} />
      <TransitionSeries.Sequence name="05 · Anticipating the arrival" durationInFrames={168}><Direction /></TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 18})} />
      <TransitionSeries.Sequence name="06 · Departure southbound" durationInFrames={258}><Departure /></TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 18})} />
      <TransitionSeries.Sequence name="07 · A second journey" durationInFrames={180}><Approach /></TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 18})} />
      <TransitionSeries.Sequence name="08 · Forecast recalled" durationInFrames={120}><ArrivalForecast /></TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 18})} />
      <TransitionSeries.Sequence name="09 · Touchdown" durationInFrames={174}><Arrival /></TransitionSeries.Sequence>
    </TransitionSeries>
    <AbsoluteFill style={{background: '#07121d', opacity: interpolate(frame, [0, 24, 1914, 1949], [1, 0, 0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}), pointerEvents: 'none'}} />
  </AbsoluteFill>;
};
