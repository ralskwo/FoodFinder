import React, { useEffect, useRef, useState } from 'react';
import './NaverMap.css';

const NAVER_MAP_KEY_ID = (
    process.env.REACT_APP_NAVER_MAP_KEY_ID ||
    process.env.REACT_APP_NAVER_MAP_CLIENT_ID ||
    ''
).trim();

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
    const [isScriptLoaded, setIsScriptLoaded] = useState(false);

    // 네이버 지도 스크립트 동적 로드
    useEffect(() => {
        if (window.naver && window.naver.maps) {
            setIsScriptLoaded(true);
            return;
        }

        if (!NAVER_MAP_KEY_ID) {
            console.error('Naver Maps Key ID is missing. Set REACT_APP_NAVER_MAP_KEY_ID in frontend/.env');
            return;
        }

        const script = document.createElement('script');
        // Naver Cloud Platform (console.ncloud.com) 사용
        script.src = `https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId=${encodeURIComponent(NAVER_MAP_KEY_ID)}`;
        script.async = true;
        script.onload = () => {
            setIsScriptLoaded(true);
        };
        script.onerror = () => {
            console.error('네이버 지도 스크립트 로드 실패');
        };
        document.head.appendChild(script);

        return () => {
            // cleanup 시 스크립트 제거하지 않음 (재사용을 위해)
        };
    }, []);

    // 지도 초기화 (스크립트 로드 후 실행)
    useEffect(() => {
        if (!isScriptLoaded || !window.naver || !mapRef.current) return;

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
                try {
                    mapInstanceRef.current.destroy();
                } catch (e) {
                    // 무시
                }
                mapInstanceRef.current = null;
            }
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isScriptLoaded]);

    // 중심 좌표 변경
    useEffect(() => {
        if (!isScriptLoaded || !window.naver || !mapInstanceRef.current || !center) return;
        const newCenter = new window.naver.maps.LatLng(center.lat, center.lng);
        mapInstanceRef.current.setCenter(newCenter);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [center.lat, center.lng, isScriptLoaded]);

    // 마커 업데이트
    useEffect(() => {
        if (!isScriptLoaded || !mapInstanceRef.current || !window.naver) return;

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
                    content: '<div class="custom-marker ' + (selectedMarkerId === markerData.id ? 'selected' : '') + '"><span>' + markerData.name.substring(0, 4) + '</span></div>',
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
    }, [markers, selectedMarkerId, onMarkerClick, isScriptLoaded]);

    const reverseGeocode = async (lat, lng) => {
        try {
            const response = await fetch('/api/geocode/reverse?lat=' + lat + '&lng=' + lng);
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
            {!isScriptLoaded && (
                <div className="map-loading">지도를 불러오는 중...</div>
            )}
            <div ref={mapRef} className="naver-map" style={{ display: isScriptLoaded ? 'block' : 'none' }} />

            {showCenterPin && isScriptLoaded && (
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
