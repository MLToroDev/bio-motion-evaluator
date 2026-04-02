import type { ReactNode } from 'react';
import './ui.css';

export function SectionHeader({ children }: { children: ReactNode }) {
  return <h2 className="section-header">{children}</h2>;
}
