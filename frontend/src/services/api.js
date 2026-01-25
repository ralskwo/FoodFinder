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
    const response = await apiClient.post('/restaurants/search', params);
    return response.data;
  } catch (error) {
    console.error('검색 실패:', error);
    throw error;
  }
};

export const updateDeliveryInfo = async (placeId, deliveryData) => {
  try {
    const response = await apiClient.post(
      `/restaurants/${placeId}/delivery`,
      deliveryData
    );
    return response.data;
  } catch (error) {
    console.error('배달 정보 업데이트 실패:', error);
    throw error;
  }
};

export const getNearbyRestaurants = async (lat, lon, maxDeliveryFee) => {
  try {
    const params = { lat, lon };
    if (maxDeliveryFee) {
      params.max_delivery_fee = maxDeliveryFee;
    }
    const response = await apiClient.get('/restaurants/nearby', { params });
    return response.data;
  } catch (error) {
    console.error('주변 맛집 조회 실패:', error);
    throw error;
  }
};

export default apiClient;
