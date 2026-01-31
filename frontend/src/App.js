import React, { useState, useEffect } from "react";
import "./App.css";
import {
    searchRestaurants,
    reverseGeocode,
    geocodeAddress,
} from "./services/api";
import FilterPanel from "./components/FilterPanel";
import DeliveryInfoModal from "./components/DeliveryInfoModal";

function App() {
    const [location, setLocation] = useState(null);
    const [locationAddress, setLocationAddress] =
        useState("위치 정보를 가져오는 중...");
    const [isLocationModalOpen, setIsLocationModalOpen] = useState(false);
    const [locationSearchQuery, setLocationSearchQuery] = useState("");
    const [searchQuery, setSearchQuery] = useState("음식점");
    const [restaurants, setRestaurants] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [filters, setFilters] = useState({
        radius: 1000,
        categories: [],
        maxDeliveryFee: null,
        maxPrice: null,
    });
    const [selectedRestaurant, setSelectedRestaurant] = useState(null);

    useEffect(() => {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const coords = {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                    };
                    setLocation(coords);
                    getAddressFromCoords(coords.latitude, coords.longitude);
                },
                (error) => {
                    console.error("위치 정보를 가져올 수 없습니다:", error);
                    const defaultCoords = {
                        latitude: 37.5665,
                        longitude: 126.978,
                    };
                    setLocation(defaultCoords);
                    setLocationAddress("서울특별시 중구 (기본 위치)");
                },
            );
        }
    }, []);

    const getAddressFromCoords = async (lat, lon) => {
        try {
            // 네이버 Reverse Geocoding API 호출
            const data = await reverseGeocode(lat, lon);
            if (data && data.address) {
                setLocationAddress(data.address);
            } else {
                setLocationAddress(
                    `위도: ${lat.toFixed(4)}, 경도: ${lon.toFixed(4)}`,
                );
            }
        } catch (error) {
            console.error("주소 변환 실패:", error);
            setLocationAddress(
                `위도: ${lat.toFixed(4)}, 경도: ${lon.toFixed(4)}`,
            );
        }
    };

    const handleFilterChange = (key, value) => {
        setFilters((prev) => ({ ...prev, [key]: value }));
    };

    const handleLocationSearch = async () => {
        if (!locationSearchQuery.trim()) return;

        try {
            const result = await geocodeAddress(locationSearchQuery);
            if (result && result.latitude && result.longitude) {
                const newLocation = {
                    latitude: result.latitude,
                    longitude: result.longitude,
                };
                setLocation(newLocation);
                if (result.address) {
                    setLocationAddress(result.address);
                } else {
                    getAddressFromCoords(result.latitude, result.longitude);
                }
                setIsLocationModalOpen(false);
                setLocationSearchQuery("");
                alert(
                    "위치가 설정되었습니다: " +
                        (result.address || locationSearchQuery),
                );
            } else {
                alert("주소를 찾을 수 없습니다.");
            }
        } catch (error) {
            console.error("위치 검색 오류:", error);
            alert("위치 검색 중 오류가 발생했습니다.");
        }
    };

    const handleSearch = async () => {
        if (!location) {
            alert("위치 정보를 불러오는 중입니다.");
            return;
        }

        setLoading(true);
        setError(null);

        try {
            // 주소에서 지역명 추출 (OSM 주소 포맷 대응: "동", "읍", "면", "구", "시" 등)
            // 예: "풍덕천동, 수지구, 용인시..." -> "용인시 수지구 풍덕천동"
            let regionQuery = "";
            if (
                locationAddress &&
                locationAddress !== "위치 정보를 가져오는 중..."
            ) {
                const parts = locationAddress.split(",").map((s) => s.trim());
                // 뒤에서부터(큰 지역부터) 찾는 게 안전함 (경기도 -> 용인시 -> 수지구 -> 풍덕천동)
                // 하지만 검색어에는 "풍덕천동" 같은 동네 이름이 가장 중요함

                // 동/읍/면 찾기
                const dong = parts.find(
                    (p) =>
                        p.endsWith("동") ||
                        p.endsWith("읍") ||
                        p.endsWith("면"),
                );
                // 구/시 찾기
                const gu = parts.find((p) => p.endsWith("구"));

                let regions = [];
                if (gu) regions.push(gu);
                if (dong) regions.push(dong);

                if (regions.length > 0) {
                    regionQuery = regions.join(" "); // "수지구 풍덕천동"
                }
            }

            // 검색어 조합 (이미 지역명이 포함되어 있으면 제외)
            let finalQuery = searchQuery;
            if (regionQuery && !searchQuery.includes(regionQuery)) {
                // 사용자가 "치킨" 입력 -> "수지구 풍덕천동 치킨"
                finalQuery = `${regionQuery} ${searchQuery}`;

                // ⭐ 사용자에게 보여주기 위해 검색창 텍스트도 업데이트
                setSearchQuery(finalQuery);
            }

            console.log("검색어 변환:", searchQuery, "->", finalQuery);

            const params = {
                query: finalQuery,
                latitude: location.latitude,
                longitude: location.longitude,
                radius: filters.radius,
            };

            if (filters.categories.length > 0) {
                params.categories = filters.categories;
            }

            const data = await searchRestaurants(params);
            setRestaurants(data.results || []);
        } catch (err) {
            setError("검색에 실패했습니다. 나중에 다시 시도해주세요.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="App">
            <header className="App-header">
                <h1>🍽️ FoodFinder - 맛집 추천</h1>
                <p>위치 기반 맞춤형 맛집 찾기</p>
                <div className="location-info">
                    <span className="location-icon">📍</span>
                    <span className="location-text">{locationAddress}</span>
                    <button
                        className="change-location-btn"
                        onClick={() => setIsLocationModalOpen(true)}>
                        위치 변경
                    </button>
                </div>
            </header>

            {isLocationModalOpen && (
                <div className="modal-overlay">
                    <div className="modal-content">
                        <h2>새로운 위치 설정</h2>
                        <p>검색할 지역이나 건물의 이름을 입력하세요.</p>
                        <div className="location-input-group">
                            <input
                                type="text"
                                className="location-input"
                                value={locationSearchQuery}
                                onChange={(e) =>
                                    setLocationSearchQuery(e.target.value)
                                }
                                placeholder="예: 강남역, 화성시청"
                                onKeyPress={(e) =>
                                    e.key === "Enter" && handleLocationSearch()
                                }
                            />
                            <button
                                className="modal-confirm-btn"
                                onClick={handleLocationSearch}>
                                검색
                            </button>
                        </div>
                        <div className="modal-actions">
                            <button
                                className="modal-close-btn"
                                onClick={() => setIsLocationModalOpen(false)}>
                                닫기
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <main className="container">
                <div className="search-section">
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="음식 종류를 입력하세요"
                        className="search-input"
                    />
                    <button
                        onClick={handleSearch}
                        className="search-button"
                        disabled={loading}>
                        {loading ? "검색 중..." : "검색"}
                    </button>
                </div>

                <FilterPanel
                    filters={filters}
                    onFilterChange={handleFilterChange}
                />

                {error && <div className="error-message">{error}</div>}

                <div className="results-section">
                    {restaurants.length > 0 ? (
                        <>
                            <h2 className="results-title">
                                검색 결과 ({restaurants.length}개)
                            </h2>
                            <div className="restaurant-list">
                                {restaurants.map((restaurant, index) => (
                                    <div
                                        key={restaurant.place_id || index}
                                        className="restaurant-card">
                                        <h3>{restaurant.title}</h3>
                                        <p className="category">
                                            {restaurant.category}
                                        </p>
                                        <p className="address">
                                            {restaurant.road_address ||
                                                restaurant.address}
                                        </p>
                                        {restaurant.distance && (
                                            <p className="distance">
                                                {restaurant.distance}m
                                            </p>
                                        )}
                                        {restaurant.telephone && (
                                            <p className="phone">
                                                {restaurant.telephone}
                                            </p>
                                        )}
                                        <button
                                            className="add-delivery-btn"
                                            onClick={() =>
                                                setSelectedRestaurant(
                                                    restaurant,
                                                )
                                            }>
                                            배달 정보 추가
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </>
                    ) : (
                        !loading && (
                            <p className="no-results">검색 결과가 없습니다.</p>
                        )
                    )}
                </div>
            </main>

            {selectedRestaurant && (
                <DeliveryInfoModal
                    restaurant={selectedRestaurant}
                    onClose={() => setSelectedRestaurant(null)}
                    onUpdate={(data) => {
                        console.log("Updated:", data);
                    }}
                />
            )}
        </div>
    );
}

export default App;
