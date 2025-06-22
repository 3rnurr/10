'use client';
import { useState, FormEvent } from 'react';
import axios from 'axios';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const router = useRouter();

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const response = await axios.post('http://localhost:8000/api/login', { username, password });
      localStorage.setItem('auth_token', response.data.access_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      router.push('/home');
    } catch (err) { setError('Неверный логин или пароль.'); }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <form onSubmit={handleLogin} className="p-8 bg-white rounded-lg shadow-md w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-6 text-center">Вход в Микроблог</h1>
        {error && <p className="text-red-500 text-center mb-4">{error}</p>}
        <div className="mb-4">
          <input type="text" value={username} onChange={e => setUsername(e.target.value)} placeholder="user1 или user2" className="w-full p-2 border rounded" />
        </div>
        <div className="mb-6">
          <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="password1 или password2" className="w-full p-2 border rounded" />
        </div>
        <button type="submit" className="w-full bg-blue-500 text-white p-2 rounded hover:bg-blue-600">Войти</button>
      </form>
    </div>
  );
}