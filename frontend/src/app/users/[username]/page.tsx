'use client';
import { useState, useEffect } from 'react';
import { use } from 'react';
import axios from 'axios';
import { useRouter } from 'next/navigation';

interface Post { 
  id: string; 
  text: string; 
  timestamp: string; 
  owner_id: string; 
  owner_username: string; 
  likes_count: number;
}
interface User { id: string; username: string; }

const API_URL = 'http://localhost:8000/api';

export default function UserProfilePage({ params }: { params: Promise<{ username: string }> }) {
  const { username } = use(params);
  const [posts, setPosts] = useState<Post[]>([]);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const fetchUserPosts = async () => {
    try {
      const res = await axios.get(`${API_URL}/users/${username}/posts`);
      setPosts(res.data);
    } catch (error) { 
      console.error("Failed to fetch user posts:", error); 
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (!storedUser) {
      router.push('/login');
      return;
    }
    
    setUser(JSON.parse(storedUser));
    fetchUserPosts();
  }, [username, router]);

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
    router.push('/login');
  };

  const handleLikePost = async (postId: string) => {
    const token = localStorage.getItem('auth_token');
    try {
      await axios.post(`${API_URL}/posts/${postId}/like`, {}, { headers: { Authorization: `Bearer ${token}` } });
      fetchUserPosts(); // Обновляем ленту
    } catch (error) { 
      console.error("Failed to like post:", error);
      // Если уже лайкнул, то убираем лайк
      try {
        await axios.delete(`${API_URL}/posts/${postId}/like`, { headers: { Authorization: `Bearer ${token}` } });
        fetchUserPosts();
      } catch (unlikeError) { console.error("Failed to unlike post:", unlikeError); }
    }
  };

  if (loading) return <p>Загрузка...</p>;
  if (!user) return <p>Перенаправление...</p>;

  return (
    <div className="container mx-auto max-w-2xl p-4">
      <header className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold">Профиль {username}</h1>
          <p className="text-gray-600">Все посты пользователя</p>
        </div>
        <div>
          <span>Привет, <strong>{user.username}</strong>!</span>
          <button onClick={() => router.push('/home')} className="ml-4 bg-blue-500 text-white py-1 px-3 rounded text-sm">На главную</button>
          <button onClick={handleLogout} className="ml-2 bg-red-500 text-white py-1 px-3 rounded text-sm">Выйти</button>
        </div>
      </header>

      <div className="space-y-4">
        {posts.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <p>У пользователя {username} пока нет постов</p>
          </div>
        ) : (
          posts.map(post => (
            <div key={post.id} className="bg-white p-4 rounded-lg shadow">
              <p>{post.text}</p>
              <div className="text-xs text-gray-500 mt-2">
                <strong>{post.owner_username}</strong> - {new Date(post.timestamp).toLocaleString()}
              </div>
              <div className="flex items-center mt-2">
                <button 
                  onClick={() => handleLikePost(post.id)} 
                  className="text-red-500 hover:text-red-700 mr-2"
                >
                  ❤️ {post.likes_count}
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
} 