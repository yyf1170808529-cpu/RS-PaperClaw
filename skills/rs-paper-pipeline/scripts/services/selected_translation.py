"""Local Argos translation for the AI-reviewed daily selection; no translation API."""


def valid_translation(english, chinese):
    from services.maritime_reading import translation_error
    return translation_error(english, chinese) is None


def chosen_zh(paper, daily=False):
    from services.maritime_reading import cached_translation
    value = paper.get('translation') or {}
    if value.get('status') == 'manual' and isinstance(value.get('zh'), str) and value['zh'].strip():
        return value['zh'], 'manual'
    if cached_translation(paper):
        return value['zh'], 'argos'
    # Historical DeepSeek results stay in selected_translation but do not override
    # the same manual/local translation used by both reading pages.
    return '', 'english_only'


def translation_issue(paper):
    from services.maritime_reading import translation_error
    from hashlib import sha256
    value = paper.get('translation') or {}
    if chosen_zh(paper)[0]:
        return ''
    if value.get('status') == 'failed':
        detail=value.get('error') or value.get('error_type') or '本地翻译失败'
        if 'Permission denied' in detail:
            return 'Argos 无法读取本地模型文件（Permission denied）'
        if value.get('error_type')=='dependency_missing':
            return '本地 Argos 翻译依赖未安装'
        if value.get('error_type')=='model_missing':
            return 'Argos 英译中模型未安装或未就绪'
        return detail
    if not paper.get('abstract'):
        return '缺少英文摘要'
    if value.get('english_hash') != sha256(paper['abstract'].encode()).hexdigest():
        return '本地译文尚未生成，或英文摘要已变化'
    return translation_error(paper['abstract'], value.get('zh')) or '本地译文尚未生成'


def translate_selected(root, library, day, config=None, seconds=180):
    from services.mobile_digest import select_daily
    from services.maritime import library_path, write_json
    from services.maritime_update import translate_budget
    chosen, _ = select_daily(root, library, day, config=config)
    keys = [p['paper_id'] for p, _, _ in chosen]
    result = translate_budget(library, keys, len(keys), seconds,
                              lambda: write_json(library_path(root), library),selected=True)
    result.update(selected=len(keys), engine='Argos Translate (CPU)', api_calls=0,
                  cost_upper_cny=0.0, priced_cost_cny=0.0)
    result['papers'] = [{'paper_id': key, 'source': chosen_zh(library['papers'][key])[1],
                        'error': translation_issue(library['papers'][key])} for key in keys]
    result['failed'] = sum(bool(p['error']) for p in result['papers'])
    return result
