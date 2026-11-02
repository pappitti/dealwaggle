// Generated with the DealWaggle design system. Needs dealwaggle.css (or css/mark.css) loaded.
import type { SVGProps } from "react";

export type DWMarkProps = Omit<SVGProps<SVGSVGElement>, "children"> & {
  /** Rendered size in px. Below 48 the bee keeps its size; at 18 and under only the bee shows. */
  size?: number;
  /** Plays the waggle dance continuously (use as a loader). It also plays on hover. */
  loading?: boolean;
  /** Accessible name. Pass "" when the mark sits next to visible text. */
  label?: string;
};

const sizeClass = (size: number) => (size <= 18 ? "dw-16" : size <= 28 ? "dw-24" : size <= 40 ? "dw-32" : "");

export function DWMark({ size = 32, loading = false, label = "DealWaggle", className, ...rest }: DWMarkProps) {
  const classes = ["dw-mark", sizeClass(size), loading && "dw-loading", className].filter(Boolean).join(" ");
  return (
    <svg
      viewBox="6 10 36 36"
      width={size}
      height={size}
      className={classes}
      role={label ? "img" : undefined}
      aria-label={label || undefined}
      aria-hidden={label ? undefined : true}
      {...rest}
    >
      <g transform="rotate(30 24 28)"><g className="dw-dance">
      <circle className="dw-orbit" cx="24" cy="28" r="12"/>
      <path className="dw-run" d="M24 40L25.8 38.5L22.2 35.5L25.8 32.5L22.2 29.5L25.8 26.5L22.2 23.5L25.8 20.5L22.2 17.5L24 16"/>
      <path className="dw-trail" pathLength="100" d="M24 28L25.8 26.5L22.2 23.5L25.8 20.5L22.2 17.5L24 16A12 12 0 0 1 24 40L25.8 38.5L22.2 35.5L25.8 32.5L22.2 29.5L25.8 26.5L22.2 23.5L25.8 20.5L22.2 17.5L24 16A12 12 0 0 0 24 40L25.8 38.5L22.2 35.5L25.8 32.5L22.2 29.5L24 28"/>
      <g className="dw-bee"><g className="dw-bee-scale"><g className="dw-bee-body">
      <g className="dw-wings"><ellipse cx="-1.2" cy="-2.8" rx="2.3" ry="1.3" transform="rotate(30 -1.2 -2.8)"/><ellipse cx="-1.2" cy="2.8" rx="2.3" ry="1.3" transform="rotate(-30 -1.2 2.8)"/></g>
      <ellipse className="dw-abdomen" cx="-.3" cy="0" rx="3.6" ry="2.4"/>
      <path className="dw-stripes" d="M-1.6 -2.1V2.1M.4 -2.2V2.2"/>
      <circle className="dw-head" cx="3.9" cy="0" r="1.5"/>
      </g></g></g>
      </g></g>
    </svg>
  );
}
