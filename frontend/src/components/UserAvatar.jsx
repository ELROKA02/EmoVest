import React, { useState, useEffect } from 'react';

const sizeClasses = {
  sm: 'w-8 h-8',
  md: 'w-10 h-10',
  lg: 'w-24 h-24',
};

const UserAvatar = ({ size = 'sm', className = '', iconClassName = '' }) => {
  const [avatar, setAvatar] = useState(() => localStorage.getItem('userAvatar') || '');

  useEffect(() => {
    const update = () => setAvatar(localStorage.getItem('userAvatar') || '');
    window.addEventListener('storage', update);
    window.addEventListener('avatarChange', update);
    return () => {
      window.removeEventListener('storage', update);
      window.removeEventListener('avatarChange', update);
    };
  }, []);

  const dimension = sizeClasses[size] || sizeClasses.sm;

  if (avatar) {
    return (
      <img
        src={avatar}
        alt="Avatar del usuario"
        className={`${dimension} rounded-full object-cover border border-white/20 ${className}`}
      />
    );
  }

  return (
    <svg className={`${dimension} ${iconClassName}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
    </svg>
  );
};

export default UserAvatar;
