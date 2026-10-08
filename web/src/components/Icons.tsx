import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

/** Ikon garis 24×24, warna mengikuti `currentColor`. */
function Icon({ size = 20, children, ...rest }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...rest}
    >
      {children}
    </svg>
  );
}

/** Logo aplikasi: mushaf terbuka di dalam bingkai bintang delapan (rub el hizb). */
export function Logo({ size = 32, className }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" className={className} role="img" aria-label="QuranRAG-ID">
      <rect width="32" height="32" rx="8" fill="var(--accent)" />
      <g fill="none" stroke="var(--accent-text)" strokeLinecap="round" strokeLinejoin="round">
        <g strokeWidth="1" opacity=".45">
          <rect x="6" y="6" width="20" height="20" rx="1.5" />
          <rect x="6" y="6" width="20" height="20" rx="1.5" transform="rotate(45 16 16)" />
        </g>
        <path
          strokeWidth="1.7"
          d="M9.5 11.4c2.3-.8 4.6-.5 6.5.9 1.9-1.4 4.2-1.7 6.5-.9v9.2c-2.3-.8-4.6-.5-6.5.9-1.9-1.4-4.2-1.7-6.5-.9z"
        />
        <path strokeWidth="1.7" d="M16 12.3v9.2" />
      </g>
    </svg>
  );
}

export const PlusIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M12 5v14M5 12h14" />
  </Icon>
);

export const MenuIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M4 7h16M4 12h16M4 17h16" />
  </Icon>
);

export const CloseIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M6 6l12 12M18 6L6 18" />
  </Icon>
);

export const AlertIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M10.3 4.3 2.7 17.5A2 2 0 0 0 4.4 20.5h15.2a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0z" />
    <path d="M12 9.5v4M12 17h.01" />
  </Icon>
);

export const ChevronRightIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M9 6l6 6-6 6" />
  </Icon>
);

export const LogoutIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 16l-4-4 4-4M6 12h10" />
  </Icon>
);

export const SendIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </Icon>
);

export const StopIcon = (p: IconProps) => (
  <Icon {...p}>
    <rect x="7" y="7" width="10" height="10" rx="1.5" fill="currentColor" stroke="none" />
  </Icon>
);
