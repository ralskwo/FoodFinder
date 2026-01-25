import React, { useState, useEffect } from 'react';
import './App.css';
import { searchRestaurants } from './services/api';

function App() {
  const [location, setLocation] = useState(null);
  const [searchQuery, setSearchQuery] = useState('한식');
  const [restaurants, setRestaurants] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLocation({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          });
        },
        (error) => {
          console.error('위치 정보를 가져올 수 없습니다:', error);
          setLocation({ latitude: 37.5665, longitude: 126.9780 });
        }
      );
    }
  }, []);

  const handleSearch = async () => {
    if (!location) {
      alert('위치 정보를 불러오는 중입니다.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await searchRestaurants({
        query: searchQuery,
        latitude: location.latitude,
        longitude: location.longitude,
        radius: 1000,
      });
      setRestaurants(data.results || []);
    } catch (err) {
      setError('검색에 실패했습니다. 나중에 다시 시도해주세요.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>FoodFinder - 맛집 추천</h1>
      </header>

      <main className="container">
        <div className="search-section">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="음식 종류를 입력하세요"
            className="search-input"
          />
          <button onClick={handleSearch} className="search-button" disabled={loading}>
            {loading ? '검색 중...' : '검색'}
          </button>
        </div>

        {error && <div className="error-message">{error}</div>}

        <div className="results-section">
          {restaurants.length > 0 ? (
            <div className="restaurant-list">
              {restaurants.map((restaurant, index) => (
                <div key={index} className="restaurant-card">
                  <h3>{restaurant.title}</h3>
                  <p className="category">{restaurant.category}</p>
                  <p className="address">{restaurant.road_address || restaurant.address}</p>
                  {restaurant.distance && <p className="distance">거리: {restaurant.distance}m</p>}
                  {restaurant.telephone && <p className="phone">{restaurant.telephone}</p>}
                </div>
              ))}
            </div>
          ) : (
            !loading && <p className="no-results">검색 결과가 없습니다.</p>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
