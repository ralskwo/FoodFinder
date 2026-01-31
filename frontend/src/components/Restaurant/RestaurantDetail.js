import React, { useState, useEffect } from "react";
import "./RestaurantDetail.css";

const RestaurantDetail = ({ restaurant, onClose }) => {
    const [menus, setMenus] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showContribute, setShowContribute] = useState(false);
    const [newMenu, setNewMenu] = useState({ name: "", price: "" });

    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(() => {
        loadMenus();
    }, [restaurant.place_id]);

    const loadMenus = async () => {
        setLoading(true);
        try {
            const response = await fetch("/api/restaurants/" + restaurant.place_id + "/menus");
            const data = await response.json();
            setMenus(data.menus || []);
        } catch (error) {
            console.error("Failed to load menus:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleContribute = async () => {
        if (!newMenu.name) return;

        try {
            await fetch("/api/restaurants/" + restaurant.place_id + "/menus/contribute", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    menu_name: newMenu.name,
                    price: newMenu.price ? parseInt(newMenu.price) : null
                })
            });
            setNewMenu({ name: "", price: "" });
            setShowContribute(false);
            loadMenus();
        } catch (error) {
            console.error("Failed to contribute menu:", error);
        }
    };

    const formatPrice = (price) => {
        if (!price) return "가격 미정";
        return price.toLocaleString() + "원";
    };

    return (
        <div className="restaurant-detail">
            <div className="detail-header">
                <button className="back-btn" onClick={onClose}>
                    ← 뒤로
                </button>
                <h2>{restaurant.name}</h2>
            </div>

            <div className="detail-info">
                <div className="info-row">
                    <span className="category">{restaurant.category}</span>
                    <span className="separator">·</span>
                    <span className="distance">{restaurant.distance}m</span>
                    {restaurant.rating && (
                        <>
                            <span className="separator">·</span>
                            <span className="rating">⭐ {restaurant.rating}</span>
                        </>
                    )}
                </div>

                {restaurant.address && (
                    <p className="address">📍 {restaurant.road_address || restaurant.address}</p>
                )}

                {restaurant.phone && (
                    <p className="phone">📞 {restaurant.phone}</p>
                )}
            </div>

            <div className="menu-section">
                <div className="menu-header">
                    <h3>메뉴</h3>
                    <button
                        className="add-menu-btn"
                        onClick={() => setShowContribute(!showContribute)}
                    >
                        + 메뉴 추가
                    </button>
                </div>

                {showContribute && (
                    <div className="contribute-form">
                        <input
                            type="text"
                            placeholder="메뉴명"
                            value={newMenu.name}
                            onChange={(e) => setNewMenu({...newMenu, name: e.target.value})}
                        />
                        <input
                            type="number"
                            placeholder="가격 (원)"
                            value={newMenu.price}
                            onChange={(e) => setNewMenu({...newMenu, price: e.target.value})}
                        />
                        <button onClick={handleContribute}>추가</button>
                    </div>
                )}

                {loading ? (
                    <p className="loading">메뉴 정보를 불러오는 중...</p>
                ) : menus.length > 0 ? (
                    <div className="menu-list">
                        {menus.map((menu, idx) => (
                            <div key={idx} className="menu-row">
                                <span className="menu-name">
                                    {menu.is_representative && "⭐ "}
                                    {menu.name}
                                </span>
                                <span className="menu-price">{formatPrice(menu.price)}</span>
                            </div>
                        ))}
                    </div>
                ) : (
                    <p className="no-menus">
                        메뉴 정보가 없습니다.
                        <br />
                        메뉴를 추가해주세요!
                    </p>
                )}
            </div>
        </div>
    );
};

export default RestaurantDetail;
