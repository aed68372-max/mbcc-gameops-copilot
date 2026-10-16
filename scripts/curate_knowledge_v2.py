"""Materialise manually verified short fact summaries. Does not scrape or copy entire pages."""
import json, pathlib, hashlib, re
ROOT=pathlib.Path(__file__).resolve().parents[1]
RES=ROOT/'src/main/resources'
rows=[]
def add(character,news,date,facts):
    for tag,text in facts:
        rows.append(dict(source_id=f'v2-{news}-{tag}',title=f'{character}：{tag}',source_url=f'https://wqmt.aisnogames.com/news/{news}',
            source_type='official',character_name=character,game_version=f'CN公告{date}',collected_at='2026-10-16',content_type='official_fact_summary',
            verification_status='verified_public_page',category='character',content=text))
add('罗睺','45','2023-07-18',[
 ('背景','罗睺出身辛迪加，早年加入FAC，完成试训后在行动部门长期执行一线任务。'),
 ('职业','罗睺官方档案标注坚韧特化（Endura）。'),
 ('异能名称','罗睺的异能名称是喋血忠卫。'),
 ('异能机制','罗睺的能力具有护卫特征，并能把防御力转化为破坏力量；这不是战斗技能数值表。'),
 ('历史经历','罗睺原小队于内海覆灭；官方档案把103年记为其行为变化的时间节点。')])
add('加洛法诺','42','2023-07-17',[
 ('职业','加洛法诺官方档案标注诡秘特化（Umbra）。'),
 ('公开身份','加洛法诺以经营裁缝店为生。'),
 ('组织','官方调查将加洛法诺确认为花园组织的情报人员，擅长伪装接近目标。'),
 ('异能名称','加洛法诺的异能名称是穿刺蚕食。'),
 ('异能机制','加洛法诺能借针眼侵蚀目标，控制侵蚀速度与范围；取出针也不能逆转已经发生的侵蚀。')])
add('曼缇斯','218','2023-09-05',[
 ('职业','曼缇斯官方档案标注诡秘特化（Umbra）。'),
 ('背景','曼缇斯曾属于黑环远征军，但档案说明其具体身份因资料缺失而无法确定。'),
 ('称呼','曼缇斯长期在内海出现；曼缇斯这个称呼来自FAC人员。'),
 ('异能名称','曼缇斯的异能名称是生物拟态。'),
 ('异能机制','曼缇斯具有高速视觉、强反射和几丁质外骨骼等生物特征，可适应黑环极端环境。')])
add('蓝鹫','917','2024-09-24',[
 ('职业','蓝鹫官方档案标注异能特化（Arcane）。'),
 ('背景','蓝鹫是狄斯城外外邦移民小镇迪希尔的创始者及实际掌控者。'),
 ('组织','蓝鹫同时领导狄斯边境的地下商业集团，其确切来历未明。'),
 ('异能名称','蓝鹫的异能名称是腐影残生。'),
 ('异能机制','蓝鹫可捕获并蓄积他人破灭的幻想，再借媒介将其转化为外显破坏力量。')])
add('玉骨','1119','2025-01-20',[
 ('职业','玉骨官方档案标注坚韧特化（Endura）。'),
 ('背景','玉骨来自东洲，以讲述故事为业，在狄斯受到追捧。'),
 ('调查','官方档案称经调查玉骨将紫藤狂厄体引入狄斯；其自述动机不能替代调查记录。'),
 ('异能名称','玉骨的异能名称是话肉白骨。'),
 ('异能机制','玉骨可借讲述创造和记录故事，将受其狂厄影响的人或物投射其中，改变故事内容会消耗其意志。')])
add('萦萦','1121','2025-01-21',[
 ('职业','萦萦官方档案标注异能特化（Arcane）。'),
 ('传说','官方档案记载东洲有将萦萦视作藤萝花仙并向其许愿的传说；这是档案所载民间传说。'),
 ('传闻','档案也记录紫藤吸取元气的相反传闻，不能把传闻直接当成已证实经历。'),
 ('异能名称','萦萦的异能名称是迷藤缚梦。'),
 ('异能机制','萦萦可用紫藤花杖幻化藤树，以花香与枝条影响精神并吸收精神力量。')])
# Added after the frozen 42-document/80-task experiment. Supplementary regression only.
for tag,text in [
 ('限定规则','2026年8月5日公告宣布开启终焉奏鸣限定追踪，丽奎安的追踪概率限时提高；公告说明概率提升结束后该限定禁闭者暂无获取途径。'),
 ('限定返场','同次公告的烬夜再临限定返场允许在瑟琳、000、奥古斯特中选择概率提升对象；未选角色不会从该返场追踪获得，活动期间可以更改选择。'),
 ('道具边界','公告说明弦音珀片可用于终焉奏鸣限定追踪和荒穹孤冕活动追踪，过期时间为2026年9月8日09:59。该历史规则不等于当前活动开放状态。')]:
    rows.append(dict(source_id='v2-2030-'+tag,title='2026周年追踪：'+tag,source_url='https://wqmt.aisnogames.com/news/2030',
        source_type='official',character_name='',game_version='CN公告2026-08-05',collected_at='2026-10-16',content_type='official_fact_summary',
        verification_status='verified_public_page',category='gameplay',content=text))
assert len(rows)==33 and len({r['source_id'] for r in rows})==33
(RES/'knowledge-v2.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
all_rows=json.loads((RES/'knowledge.json').read_text(encoding='utf-8'))+rows
index=[]
for r in all_rows:
    index.append({k:r[k] for k in ['source_id','title','source_url','source_type','game_version','collected_at','verification_status']} | {
        'published_at':re.search(r'\d{4}-\d{2}-\d{2}',r['game_version']).group(),
        'client_version':'UNKNOWN_NOT_INFERRED','summary_sha256':hashlib.sha256(r['content'].encode()).hexdigest(),
        'verification_note':'Official public page read on 2026-10-16; short human-authored summary. Ability descriptions are archival, not complete numerical skill tables.'})
(ROOT/'data').mkdir(exist_ok=True)
(ROOT/'data/source-index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'documents':len(all_rows),'new_summaries':len(rows),'distinct_urls':len({r['source_url'] for r in all_rows})}))
