import React from "react";
import "./RestaurantCard.css";

const RestaurantCard = ({ restaurant, onDetailClick, isSelected }) => {
    const formatDistance = (meters) => {
        if (meters >= 1000) {
            return (meters / 1000).toFixed(1) + "km";
        }
        return meters + "m";
    };

    const formatPrice = (price) => {
        if (!price) return "가격 미정";
        return price.toLocaleString() + "원";
    };

    return (
        <div className={"restaurant-card " + (isSelected ? "selected" : "")}>
            <div className="card-header">
                <h3 className="restaurant-name">{restaurant.name}</h3>
                {restaurant.rating && (
                    <span className="rating">⭐ {restaurant.rating.toFixed(1)}</span>
                )}
            </div>

            <div className="card-meta">
                <span className="category">{restaurant.category}</span>
                <span className="separator">·</span>
                <span className="distance">{formatDistance(restaurant.distance)}</span>
            </div>

            {restaurant.representative_menus && restaurant.representative_menus.length > 0 && (
                <div className="menu-preview">
                    {restaurant.representative_menus.map((menu, idx) => (
                        <div key={idx} className="menu-item">
                            <span className="menu-name">{menu.name}</span>
                            <span className="menu-price">{formatPrice(menu.price)}</span>
                        </div>
                    ))}
                </div>
            )}

            <button
                className="detail-btn"
                onClick={() => onDetailClick(restaurant)}
            >
                상세보기
            </button>
        </div>
    );
};

export default RestaurantCard;
