import './NavCard.css';

interface NavCardProps {
  title: string;
  subtitle: string;
  icon?: string;
  primary?: boolean;
  onClick: () => void;
}

export function NavCard({ title, subtitle, icon, primary = false, onClick }: NavCardProps) {
  return (
    <button
      type="button"
      className={`bm-nav-card ${primary ? 'bm-nav-card--primary' : ''}`}
      onClick={onClick}
    >
      {icon ? (
        <span className="bm-nav-card__icon" aria-hidden="true">
          {icon}
        </span>
      ) : null}
      <div className="bm-nav-card__content">
        <span className="bm-nav-card__title">{title}</span>
        <span className="bm-nav-card__subtitle bm-caption">{subtitle}</span>
      </div>
      <span className="bm-nav-card__arrow" aria-hidden="true" />
    </button>
  );
}
