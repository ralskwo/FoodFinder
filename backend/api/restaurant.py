from flask import Blueprint, request, jsonify
from api.naver_map import NaverMapClient
from database import db
from models.restaurant import Restaurant
from config import Config
import logging

logger = logging.getLogger(__name__)

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

    # 입력값 변환 및 검증
    try:
        query = data['query']
        latitude = float(data['latitude'])
        longitude = float(data['longitude'])
        radius = int(data.get('radius', Config.DEFAULT_SEARCH_RADIUS))
    except (ValueError, TypeError) as e:
        logger.warning(f"입력값 변환 실패: {e}")
        return jsonify({'error': '잘못된 입력값입니다'}), 400

    logger.info(f"맛집 검색 요청: query={query}, lat={latitude}, lon={longitude}")

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

    logger.info(f"검색 결과: {len(results)}개")

    return jsonify({
        'results': results,
        'count': len(results)
    }), 200


@restaurant_bp.route('/restaurants/<place_id>/delivery', methods=['POST'])
def update_delivery_info(place_id):
    """배달 정보 업데이트 (사용자 입력)"""
    data = request.get_json()

    try:
        restaurant = Restaurant.query.filter_by(place_id=place_id).first()

        if not restaurant:
            # 새로운 레스토랑 정보 생성
            restaurant = Restaurant(
                place_id=place_id,
                name=data.get('name', 'Unknown'),
                latitude=float(data.get('latitude', 0.0)),
                longitude=float(data.get('longitude', 0.0))
            )
            db.session.add(restaurant)

        # 배달 정보 업데이트
        if 'delivery_fee' in data:
            restaurant.delivery_fee = data['delivery_fee']
            restaurant.delivery_available = True

        if 'minimum_order' in data:
            restaurant.minimum_order = data['minimum_order']

        db.session.commit()
        logger.info(f"배달 정보 업데이트 완료: {place_id}")

        return jsonify(restaurant.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"배달 정보 업데이트 실패: {e}")
        return jsonify({'error': '업데이트에 실패했습니다'}), 500


@restaurant_bp.route('/restaurants/nearby', methods=['GET'])
def get_nearby_restaurants():
    """주변 맛집 조회 (배달비 필터 포함)"""
    latitude = request.args.get('lat', type=float)
    longitude = request.args.get('lon', type=float)
    max_delivery_fee = request.args.get('max_delivery_fee', type=int)

    if latitude is None or longitude is None:
        return jsonify({'error': '위치 정보는 필수입니다'}), 400

    logger.info(f"주변 맛집 조회: lat={latitude}, lon={longitude}")

    # 배달 가능한 레스토랑 조회
    query = Restaurant.query.filter_by(delivery_available=True)

    if max_delivery_fee is not None:
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
