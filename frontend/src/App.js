import React, { useState, useEffect } from 'react';
import './App.css';
import { searchRestaurants, reverseGeocode } from './services/api';
import SplitLayout from './components/Layout/SplitLayout';
import NaverMap from './components/Map/NaverMap';
import FilterPanel from './components/FilterPanel';
import RestaurantCard from './components/Restaurant/RestaurantCard';
import RestaurantDetail from './components/Restaurant/RestaurantDetail';

function App() {
    const [location, setLocation] = useState({ lat: 37.5665, lng: 126.978 });
    const [locationAddress, setLocationAddress] = useState('위치 정보를 가져오는 중...');
    const [isLocationMode, setIsLocationMode] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [restaurants, setRestaurants] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [filters, setFilters] = useState({
        radius: 1000,
        categories: [],
        budget: null,
        budgetType: 'menu'
    });
    const [selectedRestaurant, setSelectedRestaurant] = useState(null);
    const [showDetail, setShowDetail] = useState(false);

    // 초기 위치 설정
    useEffect(() => {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const coords = {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude
                    };
                    setLocation(coords);
                    getAddressFromCoords(coords.lat, coords.lng);
                },
                (error) => {
                    console.error('위치 정보를 가져올 수 없습니다:', error);
                    setLocationAddress('서울특별시 중구 (기본 위치)');
                }
            );
        }
    }, []);

    const getAddressFromCoords = async (lat, lng) => {
        try {
            const data = await reverseGeocode(lat, lng);
            if (data && data.address) {
                setLocationAddress(data.address);
            }
        } catch (error) {
            console.error('주소 변환 실패:', error);
        }
    };

    const handleFilterChange = (key, value) => {
        setFilters(prev => ({ ...prev, [key]: value }));
    };

    const handleSearch = async () => {
        setLoading(true);
        setError(null);

        try {
            const params = {
                lat: location.lat,
                lng: location.lng,
                radius: filters.radius,
                query: searchQuery || '음식점',
                budget: filters.budget,
                budgetType: filters.budgetType,
                categories: filters.categories
            };

            const data = await searchRestaurants(params);
            setRestaurants(data.results || []);
        } catch (err) {
            setError('검색에 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };

    const handleMapCenterChange = (newCenter) => {
        if (isLocationMode) {
            setLocation(newCenter);
            getAddressFromCoords(newCenter.lat, newCenter.lng);
        }
    };

    const handleSetLocation = () => {
        setIsLocationMode(false);
        handleSearch();
    };

    const handleMarkerClick = (markerData) => {
        const restaurant = restaurants.find(r => r.place_id === markerData.id);
        if (restaurant) {
            setSelectedRestaurant(restaurant);
        }
    };

    const handleDetailClick = (restaurant) => {
        setSelectedRestaurant(restaurant);
        setShowDetail(true);
    };

    const handleCloseDetail = () => {
        setShowDetail(false);
    };

    // 마커 데이터 생성
    const markers = restaurants.map(r => ({
        id: r.place_id,
        lat: r.latitude,
        lng: r.longitude,
        name: r.name
    })).filter(m => m.lat && m.lng);

    // 좌측 패널 (리스트)
    const leftPanel = (
        <div className="list-panel">
            <div className="search-section">
                <div className="location-display">
                    <span className="location-icon">📍</span>
                    <span className="location-text">{locationAddress}</span>
                    <button
                        className="location-btn"
                        onClick={() => setIsLocationMode(true)}
                    >
                        위치 변경
                    </button>
                </div>

                <div className="search-input-group">
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="검색어 입력 (예: 한식, 파스타)"
                        className="search-input"
                        onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                    />
                    <button
                        onClick={handleSearch}
                        className="search-button"
                        disabled={loading}
                    >
                        {loading ? '...' : '검색'}
                    </button>
                </div>
            </div>

            <FilterPanel filters={filters} onFilterChange={handleFilterChange} />

            {error && <div className="error-message">{error}</div>}

            <div className="results-section">
                <h3 className="results-title">
                    검색 결과 {restaurants.length}개
                    {filters.budget && ` · 예산 ${filters.budget.toLocaleString()}원 이하`}
                </h3>
                <div className="restaurant-list">
                    {restaurants.map((restaurant) => (
                        <RestaurantCard
                            key={restaurant.place_id}
                            restaurant={restaurant}
                            onDetailClick={handleDetailClick}
                            isSelected={selectedRestaurant && selectedRestaurant.place_id === restaurant.place_id}
                        />
                    ))}
                </div>
            </div>
        </div>
    );

    // 우측 패널 (지도)
    const rightPanel = (
        <div className="map-panel">
            <NaverMap
                center={location}
                onCenterChange={handleMapCenterChange}
                markers={markers}
                onMarkerClick={handleMarkerClick}
                selectedMarkerId={selectedRestaurant ? selectedRestaurant.place_id : null}
                showCenterPin={isLocationMode}
            />

            {isLocationMode && (
                <div className="location-mode-controls">
                    <p>지도를 이동하여 원하는 위치를 선택하세요</p>
                    <button onClick={handleSetLocation}>이 위치로 검색</button>
                    <button onClick={() => setIsLocationMode(false)}>취소</button>
                </div>
            )}
        </div>
    );

    // 상세 패널
    const detailPanel = selectedRestaurant && (
        <RestaurantDetail
            restaurant={selectedRestaurant}
            onClose={handleCloseDetail}
        />
    );

    return (
        <div className="App">
            <header className="App-header">
                <h1>🍽️ FoodFinder</h1>
            </header>

            <SplitLayout
                leftPanel={leftPanel}
                rightPanel={rightPanel}
                detailPanel={detailPanel}
                showDetail={showDetail}
            />
        </div>
    );
}

export default App;
