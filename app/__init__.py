"""
Flask 앱 팩토리
"""

from flask import Flask, send_from_directory
import os


def create_app(config=None):
    """Flask 앱 팩토리"""
    
    # 정적 파일 폴더 설정 (Next.js 빌드 결과물)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_folder = os.path.join(BASE_DIR, 'frontend', 'out')
    
    app = Flask(__name__, static_folder=static_folder, static_url_path='/_next_static')
    
    # 설정
    app.config['JSON_AS_ASCII'] = False  # 한글 지원
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    
    if config:
        app.config.update(config)
    
    # 블루프린트 등록
    from app.routes.kr_market import kr_bp
    from app.routes.jp_market import jp_bp
    from app.routes.us_market import us_bp
    from app.routes.common import common_bp
    
    app.register_blueprint(kr_bp, url_prefix='/api/kr')
    app.register_blueprint(jp_bp, url_prefix='/api/jp')
    app.register_blueprint(us_bp, url_prefix='/api/us')
    app.register_blueprint(common_bp, url_prefix='/api')

    
    # 캐시 비활성화 - 모든 API 응답에 no-cache 헤더 추가
    @app.after_request
    def add_no_cache_headers(response):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    
    # API 헬스체크
    @app.route('/api/health')
    def health():
        return {"status": "healthy"}
    
    # 정적 파일 서빙 및 클라이언트 사이드 라우팅 처리
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        from flask import make_response
        full_path = os.path.normpath(os.path.join(app.static_folder, path))
        
        if path != "" and os.path.exists(full_path) and os.path.isfile(full_path):
            response = make_response(send_from_directory(app.static_folder, path))
        elif path != "" and os.path.exists(full_path + '.html'):
            response = make_response(send_from_directory(app.static_folder, path + '.html'))
        else:
            response = make_response(send_from_directory(app.static_folder, 'index.html'))
        
        # HTML 파일에 UTF-8 charset 지정
        if path.endswith('.html') or path == '' or not '.' in path.split('/')[-1]:
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
        
        # 모든 정적 파일에 캐시 비활성화 헤더 추가
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    
    return app
