import React, { useState } from 'react';
import './DeliveryInfoModal.css';
import { updateDeliveryInfo } from '../services/api';

const DeliveryInfoModal = ({ restaurant, onClose, onUpdate }) => {
  const [deliveryFee, setDeliveryFee] = useState('');
  const [minimumOrder, setMinimumOrder] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const data = await updateDeliveryInfo(restaurant.place_id || `temp-${Date.now()}`, {
        delivery_fee: parseInt(deliveryFee),
        minimum_order: parseInt(minimumOrder),
        name: restaurant.title,
        latitude: restaurant.latitude,
        longitude: restaurant.longitude,
      });

      alert('배달 정보가 저장되었습니다!');
      onUpdate(data);
      onClose();
    } catch (error) {
      alert('저장에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>배달 정보 입력</h2>
        <h3>{restaurant.title}</h3>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>배달비 (원)</label>
            <input
              type="number"
              value={deliveryFee}
              onChange={(e) => setDeliveryFee(e.target.value)}
              placeholder="예: 3000"
              required
            />
          </div>

          <div className="form-group">
            <label>최소 주문 금액 (원)</label>
            <input
              type="number"
              value={minimumOrder}
              onChange={(e) => setMinimumOrder(e.target.value)}
              placeholder="예: 12000"
              required
            />
          </div>

          <div className="modal-actions">
            <button type="button" onClick={onClose} className="btn-cancel">
              취소
            </button>
            <button type="submit" className="btn-submit" disabled={loading}>
              {loading ? '저장 중...' : '저장'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default DeliveryInfoModal;
