import {Composition, Folder} from 'remotion';
import {LaunchFilm} from './LaunchFilm';
import {Cabin} from './Cabin';
import {Tower} from './Tower';
import {Product} from './Product';
import {Runway} from './Runway';
import {Direction} from './Direction';
import {Departure} from './Departure';
import {Approach} from './Approach';
import {ArrivalForecast} from './ArrivalForecast';
import {Arrival} from './Arrival';

export const RemotionRoot = () => <>
  <Composition id="FRA-Launch" component={LaunchFilm} durationInFrames={1950} fps={30} width={1920} height={1080} />
  <Folder name="Scenes">
    <Composition id="Cabin" component={Cabin} durationInFrames={300} fps={30} width={1920} height={1080} />
    <Composition id="Tower" component={Tower} durationInFrames={318} fps={30} width={1920} height={1080} />
    <Composition id="Product" component={Product} durationInFrames={348} fps={30} width={1920} height={1080} />
    <Composition id="Runway18" component={Runway} durationInFrames={228} fps={30} width={1920} height={1080} />
    <Composition id="Direction" component={Direction} durationInFrames={168} fps={30} width={1920} height={1080} />
    <Composition id="Departure" component={Departure} durationInFrames={258} fps={30} width={1920} height={1080} />
    <Composition id="Approach" component={Approach} durationInFrames={180} fps={30} width={1920} height={1080} />
    <Composition id="ArrivalForecast" component={ArrivalForecast} durationInFrames={120} fps={30} width={1920} height={1080} />
    <Composition id="Arrival" component={Arrival} durationInFrames={174} fps={30} width={1920} height={1080} />
  </Folder>
</>;
