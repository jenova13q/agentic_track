from __future__ import annotations

from app.tools_v2.contracts import ExtractionResult, SceneEntityCandidate, SceneEventCandidate, SceneFactCandidate, SceneRelationCandidate


class FakeSceneExtractionBackend:
    def extract(self, *, scene_text: str, recent_story_excerpt: str = '') -> ExtractionResult:
        text = ' '.join(scene_text.split())

        if text == 'Лев встретил Павла у пристани. Перед отплытием Лев потерял ключ.':
            return ExtractionResult(
                scene_summary='Лев встретил Павла у пристани. Перед отплытием Лев потерял ключ.',
                characters=[
                    SceneEntityCandidate(kind='character', name='Лев', canonical_name='лев', summary='Главный герой.'),
                    SceneEntityCandidate(kind='character', name='Павел', canonical_name='павел', summary='Смотритель маяка.'),
                ],
                locations=[
                    SceneEntityCandidate(kind='location', name='пристань', canonical_name='пристань', summary='Место у воды.'),
                ],
                objects=[
                    SceneEntityCandidate(kind='object', name='ключ', canonical_name='ключ', summary='Старый ключ.'),
                ],
                events=[
                    SceneEventCandidate(
                        title='Лев встретил Павла у пристани',
                        summary='Лев встретил Павла у пристани.',
                        participant_names=['Лев', 'Павел'],
                        object_names=['пристань'],
                    ),
                    SceneEventCandidate(
                        title='Перед отплытием Лев потерял ключ',
                        summary='Перед отплытием Лев потерял ключ.',
                        timeline_note='Перед отплытием',
                        temporal_relation='before',
                        participant_names=['Лев'],
                        object_names=['ключ'],
                        anchor_phrase='перед отплытием',
                    ),
                ],
                facts=[
                    SceneFactCandidate(fact_kind='object_state', summary='Лев потерял ключ.', subject_name='Лев', object_name='ключ'),
                ],
                relations=[
                    SceneRelationCandidate(left_name='Лев', right_name='Павел', relation_kind='interaction', summary='Лев встречает Павла.'),
                ],
                temporal_hints=['Перед отплытием'],
            )

        if text == 'На острове Лев вынул ключ из кармана и открыл дверь.':
            return ExtractionResult(
                scene_summary='На острове Лев вынул ключ из кармана и открыл дверь.',
                characters=[SceneEntityCandidate(kind='character', name='Лев', canonical_name='лев', summary='Главный герой.')],
                locations=[SceneEntityCandidate(kind='location', name='остров', canonical_name='остров', summary='Удалённое место.')],
                objects=[SceneEntityCandidate(kind='object', name='ключ', canonical_name='ключ', summary='Старый ключ.')],
                events=[
                    SceneEventCandidate(
                        title='Лев открыл дверь ключом на острове',
                        summary='На острове Лев вынул ключ из кармана и открыл дверь.',
                        participant_names=['Лев'],
                        object_names=['ключ'],
                    )
                ],
                facts=[
                    SceneFactCandidate(fact_kind='object_state', summary='Лев вынул ключ из кармана.', subject_name='Лев', object_name='ключ'),
                ],
            )

        if text == 'Он долго смотрел на воду и молчал.':
            return ExtractionResult(
                scene_summary='Он долго смотрел на воду и молчал.',
                facts=[SceneFactCandidate(fact_kind='scene_description', summary='Он долго смотрел на воду и молчал.')],
                unresolved_references=['он'],
            )

        if text == 'Лев был смелый. Перед выходом к воде Лев был трусливый и боялся даже посмотреть на бухту.':
            return ExtractionResult(
                scene_summary='Лев был смелый. Перед выходом к воде Лев был трусливый и боялся посмотреть на бухту.',
                characters=[SceneEntityCandidate(kind='character', name='Лев', canonical_name='лев', summary='Главный герой.')],
                facts=[
                    SceneFactCandidate(fact_kind='character_trait', summary='Лев был смелый.', subject_name='Лев'),
                    SceneFactCandidate(fact_kind='character_trait', summary='Лев был трусливый.', subject_name='Лев'),
                ],
                temporal_hints=['Перед выходом к воде'],
            )

        if text == 'Лев долго стоял у причала. Он слушал воду и не отвечал Павлу.':
            return ExtractionResult(
                scene_summary='Лев долго стоял у причала. Он слушал воду и не отвечал Павлу.',
                characters=[
                    SceneEntityCandidate(kind='character', name='Лев', canonical_name='лев', summary='Главный герой.'),
                    SceneEntityCandidate(kind='character', name='Павел', canonical_name='павел', summary='Второй герой.'),
                ],
                locations=[SceneEntityCandidate(kind='location', name='причал', canonical_name='причал', summary='Место у воды.')],
                events=[
                    SceneEventCandidate(
                        title='Лев стоял у причала',
                        summary='Лев долго стоял у причала.',
                        participant_names=['Лев'],
                        object_names=['причал'],
                    )
                ],
                facts=[SceneFactCandidate(fact_kind='scene_description', summary='Он слушал воду и не отвечал Павлу.')],
                unresolved_references=['он'],
            )

        if text == 'Перед рассветом Павел ждал Льва у причала с термосом, и они молча отвязали лодку.':
            return ExtractionResult(
                scene_summary='Перед рассветом Павел ждал Льва у причала с термосом, и они молча отвязали лодку.',
                characters=[
                    SceneEntityCandidate(kind='character', name='Павел', canonical_name='павел', summary='Смотритель маяка.'),
                    SceneEntityCandidate(kind='character', name='Лев', canonical_name='лев', summary='Главный герой.'),
                ],
                locations=[SceneEntityCandidate(kind='location', name='причал', canonical_name='причал', summary='Место у воды.')],
                objects=[
                    SceneEntityCandidate(kind='object', name='термос', canonical_name='термос', summary='Термос с чаем.'),
                    SceneEntityCandidate(kind='object', name='лодка', canonical_name='лодка', summary='Лодка для отплытия.'),
                ],
                events=[
                    SceneEventCandidate(
                        title='Перед рассветом Павел ждал Льва у причала',
                        summary='Перед рассветом Павел ждал Льва у причала с термосом, и они молча отвязали лодку.',
                        timeline_note='Перед рассветом',
                        temporal_relation='before',
                        participant_names=['Павел', 'Лев'],
                        object_names=['термос', 'лодка', 'причал'],
                        anchor_phrase='перед рассветом',
                    )
                ],
                facts=[SceneFactCandidate(fact_kind='scene_description', summary='Они молча отвязали лодку.')],
                temporal_hints=['Перед рассветом'],
                unresolved_references=['они'],
            )

        if text == 'Павел принёс колокол с острова.':
            return ExtractionResult(
                scene_summary='Павел принёс колокол с острова.',
                characters=[SceneEntityCandidate(kind='character', name='Павел', canonical_name='павел', summary='Смотритель маяка.')],
                locations=[SceneEntityCandidate(kind='location', name='остров', canonical_name='остров', summary='Удалённое место.')],
                objects=[SceneEntityCandidate(kind='object', name='колокол', canonical_name='колокол', summary='Старый корабельный колокол.')],
                events=[SceneEventCandidate(title='Павел принёс колокол с острова', summary='Павел принёс колокол с острова.', participant_names=['Павел'], object_names=['колокол', 'остров'])],
                facts=[SceneFactCandidate(fact_kind='object_state', summary='Павел принёс колокол с острова.', subject_name='Павел', object_name='колокол')],
            )

        if text == 'Лев встретил Павла у пристани.':
            return ExtractionResult(
                scene_summary='Лев встретил Павла у пристани.',
                characters=[
                    SceneEntityCandidate(kind='character', name='Лев', canonical_name='лев', summary='Главный герой.'),
                    SceneEntityCandidate(kind='character', name='Павел', canonical_name='павел', summary='Смотритель маяка.'),
                ],
                locations=[SceneEntityCandidate(kind='location', name='пристань', canonical_name='пристань', summary='Место у воды.')],
                events=[SceneEventCandidate(title='Лев встретил Павла у пристани', summary='Лев встретил Павла у пристани.', participant_names=['Лев', 'Павел'], object_names=['пристань'])],
                relations=[SceneRelationCandidate(left_name='Лев', right_name='Павел', relation_kind='interaction', summary='Лев встречает Павла.')],
            )

        if text.startswith('К вечеру Приморск всегда становился похож'):
            return ExtractionResult(
                scene_summary='К вечеру Приморск всегда становился похож на плохо вытертое зеркало.',
                characters=[
                    SceneEntityCandidate(kind='character', name='Лев', canonical_name='лев', summary='Смелый мужчина из Приморска.'),
                    SceneEntityCandidate(kind='character', name='Павел', canonical_name='павел', summary='Добрый смотритель, связанный с островом.'),
                ],
                locations=[
                    SceneEntityCandidate(kind='location', name='Приморск', canonical_name='приморск', summary='Приморский город.'),
                    SceneEntityCandidate(kind='location', name='Маячный', canonical_name='маячный', summary='Островное поселение.'),
                    SceneEntityCandidate(kind='location', name='рыбный склад', canonical_name='рыбный склад', summary='Место встречи у воды.'),
                ],
                events=[
                    SceneEventCandidate(
                        title='Павел приехал с острова',
                        summary='На следующее утро Павел приехал с острова.',
                        timeline_note='На следующее утро',
                        temporal_relation='after',
                        participant_names=['Павел'],
                        object_names=['Маячный'],
                        anchor_phrase='на следующее утро',
                    ),
                    SceneEventCandidate(
                        title='Лев встречает Павла у рыбного склада',
                        summary='Лев встречает Павла у рыбного склада.',
                        participant_names=['Лев', 'Павел'],
                        object_names=['рыбный склад'],
                    ),
                ],
                facts=[
                    SceneFactCandidate(fact_kind='scene_description', summary='К вечеру Приморск всегда становился похож на плохо вытертое зеркало.'),
                    SceneFactCandidate(fact_kind='location', summary='Лев живёт в Приморске.', subject_name='Лев', object_name='Приморск'),
                    SceneFactCandidate(fact_kind='character_trait', summary='Лев был смелый.', subject_name='Лев'),
                    SceneFactCandidate(fact_kind='location', summary='Павел живёт в Маячном.', subject_name='Павел', object_name='Маячный'),
                    SceneFactCandidate(fact_kind='character_trait', summary='Павел был добрый.', subject_name='Павел'),
                ],
                relations=[SceneRelationCandidate(left_name='Лев', right_name='Павел', relation_kind='interaction', summary='Лев встречает Павла.')],
                temporal_hints=['На следующее утро'],
            )

        raise AssertionError(f'No fake extraction prepared for scene: {scene_text!r}')
