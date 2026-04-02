import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react';
import './BmInput.css';

interface BmInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  hint?: string;
}

export function BmInput({ label, error, hint, id, ...rest }: BmInputProps) {
  const inputId = id ?? label.toLowerCase().replace(/\s+/g, '-');
  return (
    <div className="bm-field">
      <label className="bm-field__label" htmlFor={inputId}>
        {label}
      </label>
      <input
        id={inputId}
        className={`bm-field__input ${error ? 'bm-field__input--error' : ''}`}
        {...rest}
      />
      {error && (
        <span className="bm-field__error" role="alert">
          {error}
        </span>
      )}
      {!error && hint && <span className="bm-field__hint">{hint}</span>}
    </div>
  );
}

interface BmSelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  error?: string;
  hint?: string;
  children: ReactNode;
}

export function BmSelect({ label, error, hint, id, children, ...rest }: BmSelectProps) {
  const sid = id ?? label.toLowerCase().replace(/\s+/g, '-');
  return (
    <div className="bm-field">
      <label className="bm-field__label" htmlFor={sid}>
        {label}
      </label>
      <select id={sid} className={`bm-select ${error ? 'bm-field__input--error' : ''}`} {...rest}>
        {children}
      </select>
      {error && (
        <span className="bm-field__error" role="alert">
          {error}
        </span>
      )}
      {!error && hint && <span className="bm-field__hint">{hint}</span>}
    </div>
  );
}
