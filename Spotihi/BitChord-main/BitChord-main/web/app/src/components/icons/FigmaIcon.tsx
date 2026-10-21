import React from 'react';

interface FigmaIconProps {
  name: string;
  size?: number;
  className?: string;
}

// Maps Figma icon names to their SVG file paths (relative to this file)
const iconMap: Record<string, () => Promise<{ default: React.ComponentType<any> }>> = {
  'play': () => import('../../assets/icons/figma/play.svg?react'),
  'pause': () => import('../../assets/icons/figma/pause.svg?react'),
  'next': () => import('../../assets/icons/figma/next.svg?react'),
  'prev': () => import('../../assets/icons/figma/prev.svg?react'),
  'close': () => import('../../assets/icons/figma/close.svg?react'),
  'add': () => import('../../assets/icons/figma/add.svg?react'),
  'like': () => import('../../assets/icons/figma/like.svg?react'),
  'download': () => import('../../assets/icons/figma/download.svg?react'),
  'lyrics': () => import('../../assets/icons/figma/lyrics.svg?react'),
  'queue': () => import('../../assets/icons/figma/queue.svg?react'),
  'search': () => import('../../assets/icons/figma/search.svg?react'),
  'home': () => import('../../assets/icons/figma/home.svg?react'),
  'more': () => import('../../assets/icons/figma/more.svg?react'),
  'library': () => import('../../assets/icons/figma/library.svg?react'),
  'share': () => import('../../assets/icons/figma/share.svg?react'),
  'pin': () => import('../../assets/icons/figma/pin.svg?react'),
  'shuffle': () => import('../../assets/icons/figma/shuffle.svg?react'),
  'loop': () => import('../../assets/icons/figma/loop.svg?react'),
  'volume': () => import('../../assets/icons/figma/volume.svg?react'),
  'user': () => import('../../assets/icons/figma/user.svg?react'),
  'album': () => import('../../assets/icons/figma/album.svg?react'),
  'artist': () => import('../../assets/icons/figma/artist.svg?react'),
  'playlist': () => import('../../assets/icons/figma/playlist.svg?react'),
  'radio': () => import('../../assets/icons/figma/radio.svg?react'),
  'podcast': () => import('../../assets/icons/figma/podcast.svg?react'),
  'video': () => import('../../assets/icons/figma/video.svg?react'),
  'folder': () => import('../../assets/icons/figma/folder.svg?react'),
  'playing': () => import('../../assets/icons/figma/playing.svg?react'),
  'fullscreen': () => import('../../assets/icons/figma/fullscreen.svg?react'),
  'left': () => import('../../assets/icons/figma/left.svg?react'),
  'right': () => import('../../assets/icons/figma/right.svg?react'),
  'up': () => import('../../assets/icons/figma/up.svg?react'),
  'down': () => import('../../assets/icons/figma/down.svg?react'),
  'arrow-left': () => import('../../assets/icons/figma/arrow-left.svg?react'),
  'arrow-right': () => import('../../assets/icons/figma/arrow-right.svg?react'),
  'arrow-up': () => import('../../assets/icons/figma/arrow-up.svg?react'),
  'arrow-down': () => import('../../assets/icons/figma/arrow-down.svg?react'),
};

const iconCache: Record<string, React.ComponentType<any>> = {};

export function FigmaIcon({ name, size = 24, className = '' }: FigmaIconProps) {
  const [Icon, setIcon] = React.useState<React.ComponentType<any> | null>(null);

  React.useEffect(() => {
    if (iconCache[name]) {
      setIcon(iconCache[name]);
      return;
    }
    const loader = iconMap[name];
    if (loader) {
      loader().then((mod) => {
        if (mod && mod.default) {
          iconCache[name] = mod.default;
          setIcon(mod.default);
        }
      });
    }
  }, [name]);

  if (!Icon) {
    return <span style={{ width: size, height: size, display: 'inline-block' }} className={className} />;
  }

  return <Icon width={size} height={size} className={className} />;
}

export default FigmaIcon;
