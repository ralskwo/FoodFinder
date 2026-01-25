import React from 'react';
import './FilterPanel.css';

const FilterPanel = ({ filters, onFilterChange }) => {
  const categories = ['한식', '중식', '일식', '양식', '카페', '디저트', '치킨', '피자'];

  return (
    <div className="filter-panel">
      <h3>검색 필터</h3>

      <div className="filter-group">
        <label>검색 반경 (미터)</label>
        <input
          type="range"
          min="500"
          max="5000"
          step="500"
          value={filters.radius}
          onChange={(e) => onFilterChange('radius', parseInt(e.target.value))}
        />
        <span className="filter-value">{filters.radius}m</span>
      </div>

      <div className="filter-group">
        <label>음식 종류</label>
        <div className="category-chips">
          {categories.map((cat) => (
            <button
              key={cat}
              className={`chip ${filters.categories.includes(cat) ? 'active' : ''}`}
              onClick={() => {
                const newCategories = filters.categories.includes(cat)
                  ? filters.categories.filter((c) => c !== cat)
                  : [...filters.categories, cat];
                onFilterChange('categories', newCategories);
              }}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      <div className="filter-group">
        <label>최대 배달비 (원)</label>
        <input
          type="number"
          min="0"
          step="500"
          value={filters.maxDeliveryFee || ''}
          onChange={(e) => onFilterChange('maxDeliveryFee', parseInt(e.target.value) || null)}
          placeholder="제한 없음"
        />
      </div>

      <div className="filter-group">
        <label>최대 가격 (원/인)</label>
        <input
          type="number"
          min="0"
          step="1000"
          value={filters.maxPrice || ''}
          onChange={(e) => onFilterChange('maxPrice', parseInt(e.target.value) || null)}
          placeholder="제한 없음"
        />
      </div>
    </div>
  );
};

export default FilterPanel;
