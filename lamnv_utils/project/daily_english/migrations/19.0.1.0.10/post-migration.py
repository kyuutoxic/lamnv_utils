from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    changes = [
        (
            'curriculum_1_starter_daily_5',
            'Bạn tên Lan. Trả lời bằng câu đầy đủ: What is your name?',
            'What is your name? — Bạn tên là gì?',
        ),
        (
            'curriculum_1_starter_developer_5',
            'Bạn tên Lan. Trả lời bằng câu đầy đủ: What is your name?',
            'What is your name? — Bạn tên là gì?',
        ),
        (
            'curriculum_1_beginner_daily_5',
            'Bạn tên Lan. Trả lời bằng câu đầy đủ: What is your name?',
            'What is your name? — Bạn tên là gì?',
        ),
        (
            'curriculum_1_beginner_developer_5',
            'Bạn tên Lan. Trả lời bằng câu đầy đủ: What is your name?',
            'What is your name? — Bạn tên là gì?',
        ),
        (
            'curriculum_2_starter_daily_5',
            'Bạn không bận. Trả lời bằng câu đầy đủ: Are you busy?',
            'Are you busy today? — Hôm nay bạn có bận không?',
        ),
        (
            'curriculum_2_starter_developer_5',
            'Bạn không bận. Trả lời bằng câu đầy đủ: Are you busy?',
            'Are you busy today? — Hôm nay bạn có bận không?',
        ),
        (
            'curriculum_2_beginner_daily_5',
            'Bạn không bận. Trả lời bằng câu đầy đủ: Are you busy?',
            'Are you busy today? — Hôm nay bạn có bận không?',
        ),
        (
            'curriculum_2_beginner_developer_5',
            'Bạn không bận. Trả lời bằng câu đầy đủ: Are you busy?',
            'Are you busy today? — Hôm nay bạn có bận không?',
        ),
        (
            'curriculum_3_starter_daily_5',
            'Bạn muốn hỏi đồng nghiệp đã sẵn sàng chưa. Viết một câu hỏi.',
            'Hãy đặt một câu hỏi với be để hỏi thăm tôi.',
        ),
        (
            'curriculum_3_starter_developer_5',
            'Bạn muốn hỏi đồng nghiệp đã sẵn sàng chưa. Viết một câu hỏi.',
            'Hãy đặt một câu hỏi với be để hỏi thăm tôi.',
        ),
        (
            'curriculum_3_beginner_daily_5',
            'Bạn muốn hỏi đồng nghiệp đã sẵn sàng chưa. Viết một câu hỏi.',
            'Hãy đặt một câu hỏi với be để hỏi thăm tôi.',
        ),
        (
            'curriculum_3_beginner_developer_5',
            'Bạn muốn hỏi đồng nghiệp đã sẵn sàng chưa. Viết một câu hỏi.',
            'Hãy đặt một câu hỏi với be để hỏi thăm tôi.',
        ),
        (
            'curriculum_4_starter_daily_5',
            'Bạn làm việc ở nhà. Trả lời: Where do you work?',
            'Where do you work? — Bạn làm việc ở đâu?',
        ),
        (
            'curriculum_4_starter_developer_5',
            'Bạn làm việc ở nhà. Trả lời: Where do you work?',
            'Where do you work? — Bạn làm việc ở đâu?',
        ),
        (
            'curriculum_4_beginner_daily_5',
            'Bạn làm việc ở nhà. Trả lời: Where do you work?',
            'Where do you work? — Bạn làm việc ở đâu?',
        ),
        (
            'curriculum_4_beginner_developer_5',
            'Bạn làm việc ở nhà. Trả lời: Where do you work?',
            'Where do you work? — Bạn làm việc ở đâu?',
        ),
        (
            'curriculum_5_starter_daily_5',
            'Lan học tiếng Anh mỗi ngày. Nói về Lan bằng She.',
            (
                'Tell me about someone you know. — Kể về một người bạ'
                'n biết bằng he hoặc she.'
            ),
        ),
        (
            'curriculum_5_starter_developer_5',
            'Lan học tiếng Anh mỗi ngày. Nói về Lan bằng She.',
            (
                'Tell me about someone you know. — Kể về một người bạ'
                'n biết bằng he hoặc she.'
            ),
        ),
        (
            'curriculum_5_beginner_daily_5',
            'Lan học tiếng Anh mỗi ngày. Nói về Lan bằng She.',
            (
                'Tell me about someone you know. — Kể về một người bạ'
                'n biết bằng he hoặc she.'
            ),
        ),
        (
            'curriculum_5_beginner_developer_5',
            'Lan học tiếng Anh mỗi ngày. Nói về Lan bằng She.',
            (
                'Tell me about someone you know. — Kể về một người bạ'
                'n biết bằng he hoặc she.'
            ),
        ),
        (
            'curriculum_6_starter_daily_5',
            'Hỏi đồng nghiệp có uống cà phê không.',
            'Hãy hỏi tôi về một thói quen, dùng do hoặc does.',
        ),
        (
            'curriculum_6_starter_developer_5',
            'Hỏi đồng nghiệp có uống cà phê không.',
            'Hãy hỏi tôi về một thói quen, dùng do hoặc does.',
        ),
        (
            'curriculum_6_beginner_daily_5',
            'Hỏi đồng nghiệp có uống cà phê không.',
            'Hãy hỏi tôi về một thói quen, dùng do hoặc does.',
        ),
        (
            'curriculum_6_beginner_developer_5',
            'Hỏi đồng nghiệp có uống cà phê không.',
            'Hãy hỏi tôi về một thói quen, dùng do hoặc does.',
        ),
        (
            'curriculum_7_starter_daily_5',
            (
                'Bạn có thể giúp đồng nghiệp. Trả lời bằng câu đầy đủ'
                ': Can you help me?'
            ),
            'What can you do? — Bạn có thể làm gì?',
        ),
        (
            'curriculum_7_starter_developer_5',
            (
                'Bạn có thể giúp đồng nghiệp. Trả lời bằng câu đầy đủ'
                ': Can you help me?'
            ),
            'What can you do? — Bạn có thể làm gì?',
        ),
        (
            'curriculum_7_beginner_daily_5',
            (
                'Bạn có thể giúp đồng nghiệp. Trả lời bằng câu đầy đủ'
                ': Can you help me?'
            ),
            'What can you do? — Bạn có thể làm gì?',
        ),
        (
            'curriculum_7_beginner_developer_5',
            (
                'Bạn có thể giúp đồng nghiệp. Trả lời bằng câu đầy đủ'
                ': Can you help me?'
            ),
            'What can you do? — Bạn có thể làm gì?',
        ),
        (
            'curriculum_8_starter_daily_5',
            'Hôm qua bạn ở nhà. Trả lời: Where were you yesterday?',
            'Where were you yesterday? — Hôm qua bạn ở đâu?',
        ),
        (
            'curriculum_8_starter_developer_5',
            'Hôm qua bạn ở nhà. Trả lời: Where were you yesterday?',
            'Where were you yesterday? — Hôm qua bạn ở đâu?',
        ),
        (
            'curriculum_8_beginner_daily_5',
            'Hôm qua bạn ở nhà. Trả lời: Where were you yesterday?',
            'Where were you yesterday? — Hôm qua bạn ở đâu?',
        ),
        (
            'curriculum_8_beginner_developer_5',
            'Hôm qua bạn ở nhà. Trả lời: Where were you yesterday?',
            'Where were you yesterday? — Hôm qua bạn ở đâu?',
        ),
    ]
    for xmlid, old, new in changes:
        lesson = env.ref('daily_english.' + xmlid)
        if lesson.exercise == old:
            lesson.exercise = new
