import React, { useEffect, useRef, useState } from 'react';
import './NaverMap.css';

const NaverMap = ({
    center,
    onCenterChange,
    markers = [],
    onMarkerClick,
    selectedMarkerId,
    showCenterPin = false
}) => {
    const mapRef = useRef(null);
    const mapInstanceRef = useRef(null);
    const markersRef = useRef([]);
    const [address, setAddress] = useState('');

    // 지도 초기화
    useEffect(() => {
        if (!window.naver || !mapRef.current) return;

        const mapOptions = {
            center: new window.naver.maps.LatLng(center.lat, center.lng),
            zoom: 15,
            zoomControl: true,
            zoomControlOptions: {
                position: window.naver.maps.Position.TOP_RIGHT
            }
        };

        mapInstanceRef.current = new window.naver.maps.Map(mapRef.current, mapOptions);

        // 지도 이동 이벤트
        window.naver.maps.Event.addListener(mapInstanceRef.current, 'idle', () => {
            const mapCenter = mapInstanceRef.current.getCenter();
            if (onCenterChange) {
                onCenterChange({
                    lat: mapCenter.lat(),
                    lng: mapCenter.lng()
                });
            }

            // Reverse geocoding
            if (showCenterPin) {
                reverseGeocode(mapCenter.lat(), mapCenter.lng());
            }
        });

        return () => {
            if (mapInstanceRef.current) {
                mapInstanceRef.current.destroy();
            }
        };
    }, []);

    // 중심 좌표 변경
    useEffect(() => {
        if (mapInstanceRef.current && center) {
            const newCenter = new window.naver.maps.LatLng(center.lat, center.lng);
            mapInstanceRef.current.setCenter(newCenter);
        }
    }, [center.lat, center.lng]);

    // 마커 업데이트
    useEffect(() => {
        if (!mapInstanceRef.current || !window.naver) return;

        // 기존 마커 제거
        markersRef.current.forEach(marker => marker.setMap(null));
        markersRef.current = [];

        // 새 마커 추가
        markers.forEach(markerData => {
            const marker = new window.naver.maps.Marker({
                position: new window.naver.maps.LatLng(markerData.lat, markerData.lng),
                map: mapInstanceRef.current,
                title: markerData.name,
                icon: {
                    content: `<div class="custom-marker ${selectedMarkerId === markerData.id ? 'selected' : ''}">
                        <span>${markerData.name.substring(0, 4)}</span>
                    </div>`,
                    anchor: new window.naver.maps.Point(20, 40)
                }
            });

            window.naver.maps.Event.addListener(marker, 'click', () => {
                if (onMarkerClick) {
                    onMarkerClick(markerData);
                }
            });

            markersRef.current.push(marker);
        });
    }, [markers, selectedMarkerId, onMarkerClick]);

    const reverseGeocode = async (lat, lng) => {
        try {
            const response = await fetch(`/api/geocode/reverse?lat=${lat}&lng=${lng}`);
            const data = await response.json();
            if (data.address) {
                setAddress(data.address);
            }
        } catch (error) {
            console.error('Reverse geocode failed:', error);
        }
    };

    return (
        <div className="naver-map-container">
            <div ref={mapRef} className="naver-map" />

            {showCenterPin && (
                <>
                    <div className="center-pin">📍</div>
                    <div className="center-address">
                        {address || '지도를 이동하여 위치를 선택하세요'}
                    </div>
                </>
            )}
        </div>
    );
};

export default NaverMap;
