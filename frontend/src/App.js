import React, { useEffect, useState } from 'react';
import './App.css';
import { geocodeAddress, reverseGeocode, searchRestaurants } from './services/api';
import SplitLayout from './components/Layout/SplitLayout';
import NaverMap from './components/Map/NaverMap';
import FilterPanel from './components/FilterPanel';
import RestaurantCard from './components/Restaurant/RestaurantCard';
import RestaurantDetail from './components/Restaurant/RestaurantDetail';

function App() {
    const [location, setLocation] = useState({ lat: 37.5665, lng: 126.9780 });
    const [locationAddress, setLocationAddress] = useState('위치 정보를 불러오는 중...');
    const [addressQuery, setAddressQuery] = useState('');
    const [isLocationMode, setIsLocationMode] = useState(false);

    const [searchQuery, setSearchQuery] = useState('');
    const [restaurants, setRestaurants] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const [filters, setFilters] = useState({
        radius: 1000,
        categories: [],
        budget: null,
        budgetType: 'menu',
    });

    const [selectedRestaurant, setSelectedRestaurant] = useState(null);
    const [showDetail, setShowDetail] = useState(false);

    useEffect(() => {
        if (!navigator.geolocation) {
            setLocationAddress('브라우저 위치 권한을 사용할 수 없습니다.');
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const coords = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude,
                };
                setLocation(coords);
                loadAddress(coords.lat, coords.lng);
            },
            () => {
                setLocationAddress('현재 위치를 가져오지 못했습니다. 기본 위치를 사용합니다.');
            }
        );
    }, []);

    const loadAddress = async (lat, lng) => {
        try {
            const data = await reverseGeocode(lat, lng);
            if (data?.address) {
                setLocationAddress(data.address);
            }
        } catch (addressError) {
            console.error('Failed to reverse geocode', addressError);
        }
    };

    const handleFilterChange = (key, value) => {
        setFilters((prev) => ({ ...prev, [key]: value }));
    };

    const handleAddressSearch = async () => {
        if (!addressQuery.trim()) {
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const data = await geocodeAddress(addressQuery.trim());
            if (!data?.latitude || !data?.longitude) {
                throw new Error('No coordinates in geocoding response');
            }

            const coords = { lat: data.latitude, lng: data.longitude };
            setLocation(coords);
            setLocationAddress(data.address || addressQuery.trim());
            setIsLocationMode(false);

            // Move map first, then search around the selected address.
            await handleSearch(coords, data.address || addressQuery.trim());
        } catch (searchError) {
            console.error('Failed to geocode address', searchError);
            if (!searchError.response) {
                setError('백엔드 서버(5000)에 연결할 수 없습니다. run.bat으로 서버를 다시 실행해 주세요.');
            } else {
                setError('주소를 찾지 못했습니다. 주소를 더 구체적으로 입력해 주세요.');
            }
        } finally {
            setLoading(false);
        }
    };

    const handleSearch = async (overrideLocation = null, overrideLocationHint = null) => {
        setLoading(true);
        setError(null);

        try {
            const targetLocation = overrideLocation || location;
            const targetLocationHint = overrideLocationHint || locationAddress;

            const params = {
                lat: targetLocation.lat,
                lng: targetLocation.lng,
                radius: filters.radius,
                query: (searchQuery || '음식점').trim(),
                budget: filters.budget,
                budgetType: filters.budgetType,
                categories: filters.categories,
                locationHint: targetLocationHint,
            };

            const data = await searchRestaurants(params);
            setRestaurants(data.results || []);
        } catch (searchError) {
            console.error('Failed to search restaurants', searchError);
            if (!searchError.response) {
                setError('백엔드 서버(5000)에 연결할 수 없습니다. run.bat으로 서버를 다시 실행해 주세요.');
            } else {
                setError('검색에 실패했습니다. 잠시 후 다시 시도해 주세요.');
            }
        } finally {
            setLoading(false);
        }
    };

    const handleMapCenterChange = (newCenter) => {
        if (!isLocationMode) {
            return;
        }

        setLocation(newCenter);
        loadAddress(newCenter.lat, newCenter.lng);
    };

    const handleSetLocation = async () => {
        setIsLocationMode(false);
        await handleSearch(location, locationAddress);
    };

    const handleMarkerClick = (markerData) => {
        const restaurant = restaurants.find((item) => item.place_id === markerData.id);
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

    const markers = restaurants
        .map((restaurant) => ({
            id: restaurant.place_id,
            lat: restaurant.latitude,
            lng: restaurant.longitude,
            name: restaurant.name,
        }))
        .filter((marker) => Number.isFinite(marker.lat) && Number.isFinite(marker.lng));

    const leftPanel = (
        <div className="list-panel">
            <div className="search-section">
                <div className="location-display">
                    <span className="location-icon">📍</span>
                    <span className="location-text">{locationAddress}</span>
                    <button
                        className="location-btn"
                        onClick={() => setIsLocationMode(true)}
                        type="button"
                    >
                        핀으로 위치 선택
                    </button>
                </div>

                <div className="search-input-group address-search">
                    <input
                        type="text"
                        value={addressQuery}
                        onChange={(event) => setAddressQuery(event.target.value)}
                        placeholder="주소 입력 (예: 서울 강남구 테헤란로 152)"
                        className="search-input"
                        onKeyDown={(event) => event.key === 'Enter' && handleAddressSearch()}
                    />
                    <button
                        onClick={handleAddressSearch}
                        className="search-button"
                        type="button"
                        disabled={loading}
                    >
                        주소 적용
                    </button>
                </div>

                <div className="search-input-group">
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(event) => setSearchQuery(event.target.value)}
                        placeholder="음식 키워드 (예: 한식, 돈까스, 국밥)"
                        className="search-input"
                        onKeyDown={(event) => event.key === 'Enter' && handleSearch()}
                    />
                    <button
                        onClick={() => handleSearch()}
                        className="search-button"
                        type="button"
                        disabled={loading}
                    >
                        {loading ? '검색 중...' : '검색'}
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
                            isSelected={selectedRestaurant?.place_id === restaurant.place_id}
                        />
                    ))}
                </div>
            </div>
        </div>
    );

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
                    <p>지도의 중심 핀을 원하는 위치로 이동한 뒤 위치를 확정하세요.</p>
                    <button onClick={handleSetLocation} type="button">이 위치로 검색</button>
                    <button onClick={() => setIsLocationMode(false)} type="button">취소</button>
                </div>
            )}
        </div>
    );

    const detailPanel = selectedRestaurant && (
        <RestaurantDetail restaurant={selectedRestaurant} onClose={handleCloseDetail} />
    );

    return (
        <div className="App">
            <header className="App-header">
                <h1>FoodFinder</h1>
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
