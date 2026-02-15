import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const searchRestaurants = async (params) => {
    try {
        const response = await apiClient.post('/restaurants/search', {
            lat: params.latitude || params.lat,
            lng: params.longitude || params.lng,
            radius: params.radius,
            budget: params.budget,
            budget_type: params.budgetType || params.budget_type,
            categories: params.categories,
            query: params.query,
            location_hint: params.locationHint || params.location_hint,
        });
        return response.data;
    } catch (error) {
        console.error('검색 실패:', error);
        throw error;
    }
};

export const getRestaurantDetail = async (placeId) => {
    try {
        const response = await apiClient.get(`/restaurants/${placeId}`);
        return response.data;
    } catch (error) {
        console.error('상세 조회 실패:', error);
        throw error;
    }
};

export const getRestaurantMenus = async (placeId) => {
    try {
        const response = await apiClient.get(`/restaurants/${placeId}/menus`);
        return response.data;
    } catch (error) {
        console.error('메뉴 조회 실패:', error);
        throw error;
    }
};

export const contributeMenu = async (placeId, menuData) => {
    try {
        const response = await apiClient.post(`/restaurants/${placeId}/menus/contribute`, menuData);
        return response.data;
    } catch (error) {
        console.error('메뉴 추가 실패:', error);
        throw error;
    }
};

export const updateDeliveryInfo = async (placeId, deliveryData) => {
    try {
        const response = await apiClient.post(`/restaurants/${placeId}/delivery`, deliveryData);
        return response.data;
    } catch (error) {
        console.error('배달 정보 업데이트 실패:', error);
        throw error;
    }
};

export const reverseGeocode = async (lat, lng) => {
    try {
        const response = await apiClient.get('/geocode/reverse', {
            params: { lat, lng }
        });
        return response.data;
    } catch (error) {
        console.error('주소 변환 실패:', error);
        throw error;
    }
};

export const geocodeAddress = async (query) => {
    try {
        const response = await apiClient.get('/geocode', {
            params: { query }
        });
        return response.data;
    } catch (error) {
        console.error('주소 검색 실패:', error);
        throw error;
    }
};

export default apiClient;
