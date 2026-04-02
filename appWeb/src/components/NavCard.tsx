import './ui.css';

export function NavCard({
  title,
  subtitle,
  icon,
  onClick,
}: {
  title: string;
  subtitle: string;
  icon: string;
  onClick: () => void;
}) {
  return (
    <button type="button" className="nav-card" onClick={onClick}>
      <span className="nav-card__icon" aria-hidden>
        {icon}
      </span>
      <div>
        <div className="nav-card__title">{title}</div>
        <div className="nav-card__subtitle">{subtitle}</div>
      </div>
    </button>
  );
}
