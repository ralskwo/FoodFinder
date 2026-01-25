from flask import Blueprint, request, jsonify
from backend.api.naver_map import NaverMapClient
from backend.database import db
from backend.models.restaurant import Restaurant
from backend.config import Config

restaurant_bp = Blueprint('restaurant', __name__)


@restaurant_bp.route('/restaurants/search', methods=['POST'])
def search_restaurants():
    """맛집 검색 API"""
    data = request.get_json()

    # 필수 파라미터 검증
    if not data or 'query' not in data:
        return jsonify({'error': '검색어는 필수입니다'}), 400

    if 'latitude' not in data or 'longitude' not in data:
        return jsonify({'error': '위치 정보는 필수입니다'}), 400

    query = data['query']
    latitude = float(data['latitude'])
    longitude = float(data['longitude'])
    radius = data.get('radius', Config.DEFAULT_SEARCH_RADIUS)

    # 네이버 API 호출
    naver_client = NaverMapClient(
        Config.NAVER_CLIENT_ID,
        Config.NAVER_CLIENT_SECRET
    )

    results = naver_client.search_local(
        query=query,
        latitude=latitude,
        longitude=longitude,
        radius=radius
    )

    # 카테고리 필터 적용
    if 'categories' in data and data['categories']:
        categories = data['categories']
        results = [r for r in results if r.get('category') in categories]

    return jsonify({
        'results': results,
        'count': len(results)
    }), 200


@restaurant_bp.route('/restaurants/<place_id>/delivery', methods=['POST'])
def update_delivery_info(place_id):
    """배달 정보 업데이트 (사용자 입력)"""
    data = request.get_json()

    restaurant = Restaurant.query.filter_by(place_id=place_id).first()

    if not restaurant:
        # 새로운 레스토랑 정보 생성 - 필수 필드 포함
        restaurant = Restaurant(
            place_id=place_id,
            name=data.get('name', 'Unknown'),
            latitude=data.get('latitude', 0.0),
            longitude=data.get('longitude', 0.0)
        )
        db.session.add(restaurant)

    # 배달 정보 업데이트
    if 'delivery_fee' in data:
        restaurant.delivery_fee = data['delivery_fee']
        restaurant.delivery_available = True

    if 'minimum_order' in data:
        restaurant.minimum_order = data['minimum_order']

    db.session.commit()

    return jsonify(restaurant.to_dict()), 200


@restaurant_bp.route('/restaurants/nearby', methods=['GET'])
def get_nearby_restaurants():
    """주변 맛집 조회 (배달비 필터 포함)"""
    latitude = request.args.get('lat', type=float)
    longitude = request.args.get('lon', type=float)
    max_delivery_fee = request.args.get('max_delivery_fee', type=int)

    if not latitude or not longitude:
        return jsonify({'error': '위치 정보는 필수입니다'}), 400

    # 배달 가능한 레스토랑 조회
    query = Restaurant.query.filter_by(delivery_available=True)

    if max_delivery_fee:
        query = query.filter(Restaurant.delivery_fee <= max_delivery_fee)

    restaurants = query.all()

    # 거리 계산 및 정렬
    results = []
    for r in restaurants:
        lat_diff = abs(r.latitude - latitude) * 111000
        lon_diff = abs(r.longitude - longitude) * 88000
        distance = (lat_diff ** 2 + lon_diff ** 2) ** 0.5

        if distance <= 3000:  # 3km 이내
            result = r.to_dict()
            result['distance'] = int(distance)
            results.append(result)

    results.sort(key=lambda x: x['distance'])

    return jsonify({
        'results': results,
        'count': len(results)
    }), 200
