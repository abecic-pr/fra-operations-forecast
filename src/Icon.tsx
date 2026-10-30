type IconName = 'sparkles' | 'send' | 'takeoff' | 'back' | 'map' | 'grid' | 'layers' | 'locate' | 'plus' | 'minus' | 'wind' | 'arrow' | 'chevron' | 'close' | 'play' | 'pause' | 'refresh';
const paths: Record<IconName, string> = {
  sparkles: 'm12 2 2.8 7.2L22 12l-7.2 2.8L12 22l-2.8-7.2L2 12l7.2-2.8L12 2Zm7 0v4m-2-2h4',
  send: 'm5 14 7-7 7 7M12 7v14',
  takeoff: 'M3 20h18M4 14l5 1 7-6 3-1 1 2-9 8-7-1-1-2 1-1ZM10 14 7 9l2-1 5 3',
  play: 'm8 4 12 8-12 8V4Z', pause: 'M8 5v14M16 5v14',
  refresh: 'M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 11-2l3 7M4 12l3 7a7 7 0 0 0 11-2',
  back: 'm14 5-7 7 7 7', map: 'm3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3V6Zm6-3v15m6-12v15',
  grid: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
  layers: 'm3 7 9-5 9 5-9 5-9-5Zm0 5 9 5 9-5M3 17l9 5 9-5',
  locate: 'M12 2v4m0 12v4M2 12h4m12 0h4M18 12a6 6 0 1 1-12 0 6 6 0 0 1 12 0Z',
  plus: 'M12 5v14M5 12h14', minus: 'M5 12h14',
  wind: 'M3 8h12a3 3 0 1 0-3-3M3 12h16a3 3 0 1 1-3 3M3 16h6a3 3 0 1 1-3 3',
  arrow: 'M5 12h14m-6-6 6 6-6 6', chevron: 'm7 10 5 5 5-5', close: 'm6 6 12 12M6 18 18 6',
};
export default function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>;
}
