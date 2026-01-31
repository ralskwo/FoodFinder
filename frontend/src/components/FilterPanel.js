import React, { useState } from 'react';
import './FilterPanel.css';

const FilterPanel = ({ filters, onFilterChange }) => {
    const [customBudget, setCustomBudget] = useState('');

    const categories = [
        '전체', '한식', '중식', '일식', '양식', '분식',
        '카페/디저트', '패스트푸드', '치킨', '피자',
        '아시안', '멕시칸', '샐러드/건강식', '술집/호프', '베이커리'
    ];

    const budgetPresets = [5000, 10000, 15000, 20000, 30000];

    const handleBudgetPreset = (value) => {
        onFilterChange('budget', value);
        setCustomBudget('');
    };

    const handleCustomBudget = () => {
        const value = parseInt(customBudget);
        if (value > 0) {
            onFilterChange('budget', value);
        }
    };

    const handleCategoryClick = (cat) => {
        if (cat === '전체') {
            onFilterChange('categories', []);
        } else {
            const newCategories = filters.categories.includes(cat)
                ? filters.categories.filter(c => c !== cat)
                : [...filters.categories, cat];
            onFilterChange('categories', newCategories);
        }
    };

    const formatPrice = (price) => {
        if (price >= 10000) {
            return `${price / 10000}만원`;
        }
        return `${price.toLocaleString()}원`;
    };

    return (
        <div className="filter-panel">
            {/* 반경 필터 */}
            <div className="filter-group">
                <label className="filter-label">
                    📍 검색 반경
                    <span className="filter-value">{(filters.radius / 1000).toFixed(1)}km</span>
                </label>
                <input
                    type="range"
                    min="100"
                    max="5000"
                    step="100"
                    value={filters.radius}
                    onChange={(e) => onFilterChange('radius', parseInt(e.target.value))}
                    className="range-slider"
                />
                <div className="range-labels">
                    <span>100m</span>
                    <span>5km</span>
                </div>
            </div>

            {/* 예산 필터 */}
            <div className="filter-group">
                <label className="filter-label">
                    💰 예산
                    {filters.budget && (
                        <span className="filter-value">{formatPrice(filters.budget)}</span>
                    )}
                </label>

                {/* 프리셋 버튼 */}
                <div className="budget-presets">
                    {budgetPresets.map(preset => (
                        <button
                            key={preset}
                            className={`preset-btn ${filters.budget === preset ? 'active' : ''}`}
                            onClick={() => handleBudgetPreset(preset)}
                        >
                            {formatPrice(preset)}
                        </button>
                    ))}
                </div>

                {/* 슬라이더 */}
                <input
                    type="range"
                    min="1000"
                    max="50000"
                    step="1000"
                    value={filters.budget || 15000}
                    onChange={(e) => onFilterChange('budget', parseInt(e.target.value))}
                    className="range-slider"
                />

                {/* 직접 입력 */}
                <div className="custom-budget">
                    <input
                        type="number"
                        placeholder="직접 입력"
                        value={customBudget}
                        onChange={(e) => setCustomBudget(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleCustomBudget()}
                    />
                    <button onClick={handleCustomBudget}>적용</button>
                </div>

                {/* 예산 기준 */}
                <div className="budget-type">
                    <label>
                        <input
                            type="radio"
                            name="budgetType"
                            checked={filters.budgetType === 'menu'}
                            onChange={() => onFilterChange('budgetType', 'menu')}
                        />
                        메뉴 기준
                    </label>
                    <label>
                        <input
                            type="radio"
                            name="budgetType"
                            checked={filters.budgetType === 'average'}
                            onChange={() => onFilterChange('budgetType', 'average')}
                        />
                        평균 기준
                    </label>
                </div>
            </div>

            {/* 카테고리 필터 */}
            <div className="filter-group">
                <label className="filter-label">🍽️ 카테고리</label>
                <div className="category-chips">
                    {categories.map(cat => (
                        <button
                            key={cat}
                            className={`chip ${
                                cat === '전체'
                                    ? filters.categories.length === 0 ? 'active' : ''
                                    : filters.categories.includes(cat) ? 'active' : ''
                            }`}
                            onClick={() => handleCategoryClick(cat)}
                        >
                            {cat}
                        </button>
                    ))}
                </div>
            </div>

            {/* 필터 초기화 */}
            <button
                className="reset-filters"
                onClick={() => {
                    onFilterChange('radius', 1000);
                    onFilterChange('budget', null);
                    onFilterChange('budgetType', 'menu');
                    onFilterChange('categories', []);
                }}
            >
                필터 초기화
            </button>
        </div>
    );
};

export default FilterPanel;
