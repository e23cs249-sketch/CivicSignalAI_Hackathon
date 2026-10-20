document.querySelectorAll('[data-citizen-logout]').forEach((button) => {
  button.addEventListener('click', async () => {
    button.disabled = true;
    const originalText = button.textContent;
    button.textContent = 'Signing out…';

    try {
      const response = await fetch('/api/auth/citizen/logout', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { Accept: 'application/json' },
      });
      if (!response.ok) throw new Error('Sign out failed. Please retry.');
      window.location.replace('/');
    } catch (error) {
      button.disabled = false;
      button.textContent = originalText;
      window.alert(error instanceof Error ? error.message : 'Sign out failed. Please retry.');
    }
  });
});
