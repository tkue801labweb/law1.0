import os
from bson import ObjectId
from flask import Flask, jsonify, render_template, request
from src.utils.mongodb import get_database
from src.mongodb_read_data import RegulationQueryService


class WebApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.query_service = RegulationQueryService()
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/')
        def index():
            return render_template('index.html')

        @self.app.route('/regulation/<title>')
        def show_regulation(title: str):
            content = self.get_regulation_content(title)
            return render_template('regulation.html', content=content)

        @self.app.route('/api/hierarchy/<entry_id>')
        def get_hierarchy(entry_id: str):
            try:
                hierarchy_path = self.query_service.concate_ancestor_entries_unit_number(entry_id)
                return jsonify({'hierarchy': hierarchy_path})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/regulation_search/<regulation_title>')
        def search_entries(regulation_title: str):
            keyword = request.args.get('keyword', '').strip()
            if not keyword:
                return jsonify({'entries': []})
            try:
                db = get_database()
                reg = db['regulations'].find_one({'title': regulation_title})
                if not reg:
                    return jsonify({'entries': []})
                query = {
                    'regulation_id': reg['_id'],
                    'content': {'$regex': keyword, '$options': 'i'}
                }
                entries = list(db['entries'].find(query))
                return jsonify({
                    'entries': [{'_id': str(e['_id']), 'content': e['content']} for e in entries]
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/health')
        def health_check():
            return jsonify({"status": "healthy"}), 200

    def get_regulation_content(self, regulation_title: str) -> dict:
        db = get_database()
        regulation = db['regulations'].find_one({'title': regulation_title})
        if not regulation:
            return {
                'meta_data': f'⚠️ 無法找到名為「{regulation_title}」的法規。',
                'entries': [],
                'title': regulation_title
            }

        entries = list(db['entries'].find({'regulation_id': regulation['_id']}))
        return {
            'meta_data': regulation.get('meta_data', ''),
            'entries': entries,
            'title': regulation_title
        }

    def run(self):
        port = int(os.environ.get('PORT', 8000))
        self.app.run(host='0.0.0.0', port=port)


if __name__ == '__main__':
    app = WebApp()
    app.run()
