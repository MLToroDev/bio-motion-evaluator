import type { ButtonHTMLAttributes, ReactNode } from 'react';
import './BmButton.css';

type ButtonVariant = 'primary' | 'outline' | 'ghost';

interface BmButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  loading?: boolean;
  children?: ReactNode;
}

export function BmButton({
  variant = 'outline',
  loading = false,
  disabled,
  children,
  className = '',
  type = 'button',
  ...rest
}: BmButtonProps) {
  return (
    <button
      type={type}
      className={`bm-btn bm-btn--${variant} ${className}`.trim()}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? <span className="bm-btn__spinner" aria-hidden="true" /> : null}
      {children}
    </button>
  );
}
