from pathlib import Path
from bson import ObjectId
from src.utils.mongodb import get_database, get_regulation_id


class RegulationQueryService:
    def __init__(self):
        self.db = get_database()
        self.entries = self.db['entries']

    def full_text_search(self, search_text: str):
        query = {'content': {'$regex': search_text}}
        results = self.entries.find(query)
        return list(results)

    def context_entries_search(self, entry_id: str):
        if isinstance(entry_id, str):
            entry_id = ObjectId(entry_id)

        result = self.entries.aggregate([
            {'$match': {'_id': entry_id}},
            {
                '$graphLookup': {
                    'from': 'entries',
                    'startWith': '$parent_id',
                    'connectFromField': 'parent_id',
                    'connectToField': '_id',
                    'as': 'ancestors',
                    'depthField': 'ancestorLevel'
                }
            },
            {
                '$graphLookup': {
                    'from': 'entries',
                    'startWith': '$_id',
                    'connectFromField': '_id',
                    'connectToField': 'parent_id',
                    'as': 'descendants',
                    'depthField': 'descendantLevel'
                }
            }
        ])

        result = list(result)
        if len(result) != 1:
            raise ValueError(f'Expected 1 result, got {len(result)}')
        return result[0]

    def concate_ancestor_entries_content(self, entry_id: str):
        data = self.context_entries_search(entry_id)
        this_content = data['content']
        ancestors = data['ancestors']
        ancestors.sort(key=lambda x: x['ancestorLevel'], reverse=True)
        result = ''.join([a['content'] + '\n' for a in ancestors])
        result += this_content
        return result

    def concate_ancestor_entries_unit_number(self, entry_id: str):
        data = self.context_entries_search(entry_id)
        this_unit = data.get('unit_number', '')
        ancestors = data['ancestors']
        ancestors.sort(key=lambda x: x['ancestorLevel'], reverse=True)
        units = [a.get('unit_number', '') for a in ancestors]
        units.append(this_unit)
        return ', '.join(units)

    def deduplicate_content_list(self, content_list: list):
        content_list.sort(key=len)
        for i, content in enumerate(content_list):
            for j in range(i + 1, len(content_list)):
                if content in content_list[j]:
                    content_list[j] = ''
        return [c for c in content_list if c]

    def save_regulation_entries(self, regulation_title: str, save_dir: str):
        save_path = Path(save_dir) / regulation_title
        save_path.mkdir(parents=True, exist_ok=True)
        reg_id = get_regulation_id(self.db, regulation_title)
        query = {'regulation_id': reg_id}
        docs = self.entries.find(query)
        for doc in docs:
            filename = doc['content'].split('\n')[0].strip()
            file_path = save_path / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(doc['content'])
