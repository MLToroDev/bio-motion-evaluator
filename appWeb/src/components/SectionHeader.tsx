import type { ReactNode } from 'react';
import './SectionHeader.css';

interface SectionHeaderProps {
  children: ReactNode;
}

export function SectionHeader({ children }: SectionHeaderProps) {
  return (
    <div className="bm-section-header-wrap">
      <h2 className="bm-section-header__text">{children}</h2>
      <div className="bm-section-header__rule" />
    </div>
  );
}
