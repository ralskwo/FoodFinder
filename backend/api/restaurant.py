from flask import Blueprint, request, jsonify
from api.naver_map import NaverMapClient
from api.naver_geocoding import NaverGeocodingClient
from database import db
from models.restaurant import Restaurant
from models.menu import Menu
from services.menu_service import MenuService
from config import Config
import logging
import math

logger = logging.getLogger(__name__)

restaurant_bp = Blueprint('restaurant', __name__)
menu_service = MenuService()


def haversine_distance(lat1, lon1, lat2, lon2):
    """하버사인 공식으로 두 좌표 간 거리 계산 (미터)"""
    R = 6371000  # 지구 반경 (미터)

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


@restaurant_bp.route('/geocode/reverse', methods=['GET'])
def reverse_geocode():
    """좌표를 주소로 변환"""
    latitude = request.args.get('lat', type=float)
    longitude = request.args.get('lng', type=float) or request.args.get('lon', type=float)

    if latitude is None or longitude is None:
        return jsonify({'error': '위도와 경도는 필수입니다'}), 400

    geocoding_client = NaverGeocodingClient(
        Config.NAVER_CLOUD_ID,
        Config.NAVER_CLOUD_SECRET
    )

    address = geocoding_client.coord_to_address(longitude, latitude)

    if address:
        return jsonify({
            'address': address,
            'latitude': latitude,
            'longitude': longitude
        }), 200
    else:
        return jsonify({
            'address': f'위도: {latitude:.4f}, 경도: {longitude:.4f}',
            'latitude': latitude,
            'longitude': longitude
        }), 200


@restaurant_bp.route('/geocode', methods=['GET'])
def geocode_address():
    """주소를 좌표로 변환"""
    query = request.args.get('query')

    if not query:
        return jsonify({'error': '검색어를 입력하세요'}), 400

    geocoding_client = NaverGeocodingClient(
        Config.NAVER_CLOUD_ID,
        Config.NAVER_CLOUD_SECRET
    )

    result = geocoding_client.address_to_coord(query)

    if result:
        return jsonify(result), 200
    else:
        return jsonify({'error': '주소를 찾을 수 없습니다'}), 404


@restaurant_bp.route('/restaurants/search', methods=['POST'])
def search_restaurants():
    """
    맛집 검색 API (예산 필터링 포함)

    Request Body:
    {
        "lat": 37.5665,
        "lng": 126.9780,
        "radius": 2000,
        "budget": 12000,
        "budget_type": "menu",
        "categories": ["한식"],
        "query": "음식점"
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': '요청 데이터가 없습니다'}), 400

    lat = data.get('lat') or data.get('latitude')
    lng = data.get('lng') or data.get('longitude')

    if lat is None or lng is None:
        return jsonify({'error': '위치 정보는 필수입니다'}), 400

    try:
        lat = float(lat)
        lng = float(lng)
        radius = int(data.get('radius', Config.DEFAULT_SEARCH_RADIUS))
        budget = data.get('budget')
        budget_type = data.get('budget_type', 'menu')
        categories = data.get('categories', [])
        query = data.get('query', '음식점')
    except (ValueError, TypeError) as e:
        return jsonify({'error': '잘못된 입력값입니다'}), 400

    logger.info(f"Search: query={query}, lat={lat}, lng={lng}, radius={radius}, budget={budget}")

    naver_client = NaverMapClient(
        Config.NAVER_CLIENT_ID,
        Config.NAVER_CLIENT_SECRET,
        geocoding_client_id=Config.NAVER_CLOUD_ID,
        geocoding_client_secret=Config.NAVER_CLOUD_SECRET
    )

    raw_results = naver_client.search_local(
        query=query,
        latitude=lat,
        longitude=lng,
        radius=radius
    )

    results = []
    for item in raw_results:
        # 거리 재계산 (하버사인)
        if item.get('latitude') and item.get('longitude'):
            distance = haversine_distance(lat, lng, item['latitude'], item['longitude'])

            if distance > radius:
                continue

            item['distance'] = int(distance)

        # 카테고리 필터
        if categories:
            item_category = item.get('category', '')
            if not any(cat in item_category for cat in categories):
                continue

        # DB에서 음식점 조회 또는 생성
        restaurant = get_or_create_restaurant(item)

        # 메뉴 정보 조회
        menus = menu_service.get_menus(restaurant, item.get('link'))

        # 예산 필터링
        if budget and menus:
            if budget_type == 'menu':
                has_affordable = any(m.price and m.price <= budget for m in menus)
                if not has_affordable:
                    continue
            elif budget_type == 'average':
                prices = [m.price for m in menus if m.price]
                if prices:
                    avg_price = sum(prices) / len(prices)
                    if avg_price > budget:
                        continue

        # 대표 메뉴 추출
        representative_menus = [
            {'name': m.name, 'price': m.price}
            for m in menus if m.is_representative
        ][:2]

        if not representative_menus and menus:
            sorted_menus = sorted([m for m in menus if m.price], key=lambda x: x.price)
            representative_menus = [
                {'name': m.name, 'price': m.price}
                for m in sorted_menus[:2]
            ]

        results.append({
            'place_id': restaurant.place_id,
            'name': item['title'],
            'category': item.get('category', ''),
            'address': item.get('address', ''),
            'road_address': item.get('road_address', ''),
            'latitude': item.get('latitude'),
            'longitude': item.get('longitude'),
            'distance': item.get('distance'),
            'phone': item.get('telephone', ''),
            'rating': restaurant.rating,
            'representative_menus': representative_menus,
            'link': item.get('link', '')
        })

    results.sort(key=lambda x: x.get('distance', 999999))

    return jsonify({
        'results': results,
        'total': len(results),
        'filters_applied': {
            'radius': radius,
            'budget': budget,
            'budget_type': budget_type if budget else None,
            'categories': categories
        }
    }), 200


def get_or_create_restaurant(item: dict) -> Restaurant:
    """음식점 DB 조회 또는 생성"""
    place_id = item.get('link', '') or f"{item['title']}_{item.get('address', '')}"
    place_id = str(hash(place_id))[:20]

    restaurant = Restaurant.query.filter_by(place_id=place_id).first()

    if not restaurant:
        restaurant = Restaurant(
            place_id=place_id,
            name=item['title'],
            category=item.get('category', ''),
            address=item.get('address', ''),
            road_address=item.get('road_address', ''),
            latitude=item.get('latitude') or 0.0,
            longitude=item.get('longitude') or 0.0,
            phone=item.get('telephone', '')
        )
        db.session.add(restaurant)
        try:
            db.session.commit()
        except:
            db.session.rollback()
            restaurant = Restaurant.query.filter_by(place_id=place_id).first()

    return restaurant


@restaurant_bp.route('/restaurants/<place_id>', methods=['GET'])
def get_restaurant_detail(place_id):
    """음식점 상세 정보"""
    restaurant = Restaurant.query.filter_by(place_id=place_id).first()

    if not restaurant:
        return jsonify({'error': '음식점을 찾을 수 없습니다'}), 404

    return jsonify(restaurant.to_dict()), 200


@restaurant_bp.route('/restaurants/<place_id>/menus', methods=['GET'])
def get_restaurant_menus(place_id):
    """음식점 전체 메뉴 목록"""
    restaurant = Restaurant.query.filter_by(place_id=place_id).first()

    if not restaurant:
        return jsonify({'error': '음식점을 찾을 수 없습니다'}), 404

    menus = menu_service.get_menus(restaurant)

    return jsonify({
        'restaurant_id': restaurant.id,
        'restaurant_name': restaurant.name,
        'menus': [m.to_dict() for m in menus]
    }), 200


@restaurant_bp.route('/restaurants/<place_id>/menus/contribute', methods=['POST'])
def contribute_menu(place_id):
    """사용자 메뉴 정보 입력"""
    data = request.get_json()

    if not data or 'menu_name' not in data:
        return jsonify({'error': '메뉴명은 필수입니다'}), 400

    restaurant = Restaurant.query.filter_by(place_id=place_id).first()

    if not restaurant:
        return jsonify({'error': '음식점을 찾을 수 없습니다'}), 404

    menu = menu_service.add_user_contribution(
        restaurant.id,
        data['menu_name'],
        data.get('price')
    )

    if menu:
        return jsonify(menu.to_dict()), 201
    else:
        return jsonify({'error': '메뉴 추가에 실패했습니다'}), 500


@restaurant_bp.route('/restaurants/<place_id>/delivery', methods=['POST'])
def update_delivery_info(place_id):
    """배달 정보 업데이트 (사용자 입력)"""
    data = request.get_json()

    try:
        restaurant = Restaurant.query.filter_by(place_id=place_id).first()

        if not restaurant:
            restaurant = Restaurant(
                place_id=place_id,
                name=data.get('name', 'Unknown'),
                latitude=float(data.get('latitude', 0.0)),
                longitude=float(data.get('longitude', 0.0))
            )
            db.session.add(restaurant)

        if 'delivery_fee' in data:
            restaurant.delivery_fee = data['delivery_fee']
            restaurant.delivery_available = True

        if 'minimum_order' in data:
            restaurant.minimum_order = data['minimum_order']

        db.session.commit()

        return jsonify(restaurant.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"배달 정보 업데이트 실패: {e}")
        return jsonify({'error': '업데이트에 실패했습니다'}), 500
