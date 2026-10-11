# Daily English — context Odoo 19

## 1. Phạm vi và nguồn

Addon project/daily_english, version 19.0.1.0.10. Phụ thuộc base, web và
web_responsive OCA. Dùng REST urllib, không cần SDK AI hay queue_job.
Chỉ admin Odoo quản lý dữ liệu; Telegram chỉ nhận chat private ghép nối.
Icon sách/Aa tại static/description/icon.png và icon.svg.

| Nghiệp vụ | Source |
| --- | --- |
| Gemini, 9Router, Telegram, cấu hình | models/english_configuration.py |
| Bài, schema nội dung, render | models/english_lesson.py |
| Lộ trình, dạng bài, sổ lỗi sai | models/english_curriculum.py |
| Hồ sơ, lịch học, command, ghép nối | models/english_learner.py |
| Buổi học, lịch sử, dọn dữ liệu | models/english_session.py |
| Tiến độ, câu trả lời, ôn tập | models/english_progress.py |
| Gọi AI, quota, retry, lease | models/english_job.py |
| Outbox, chia tin, retry | models/english_delivery.py |
| Receipt, chống replay | models/english_update.py |
| Webhook HTTP | controllers/telegram_webhook.py |
| Views, ACL, cron, bài mẫu | views/, security/, data/ |
| Sửa dữ liệu seed cũ và tác vụ cũ | migrations/19.0.1.0.7/post-migration.py |

## 2. Luồng học và trạng thái

/lesson, Gửi bài ngay hoặc lịch hằng ngày mở/tiếp tục buổi 5 câu. Buổi
lưu thành english.session riêng, gồm ngày, level/topic, trạng thái,
các bài đã chuẩn bị/hoàn thành, số câu, số đúng, số bỏ qua, số lỗi và
câu mẫu/ngữ pháp tổng kết. Các bộ đếm trên learner phản ánh buổi hiện tại.
Buổi thủ công được phép nhiều lần/ngày; daily_date có unique theo learner.
Chỉ một câu current_progress ở trạng thái awaiting/grading tại một thời điểm.

Đúng: nhận xét, cập nhật ôn, tự sang câu tiếp nếu buổi còn hoạt động.
Sai: hiện câu sửa, đặt answer_shown=True; thử lại được nhưng không tăng
mức ghi nhớ. Xem /answer hoặc nhận giải thích AI cũng là hỗ trợ đáp án.
Attempt ghi lại việc đã xem đáp án, kể cả xem trong khi AI đang chấm.
Review_step tối đa 4, lịch ôn 1/3/7/14 ngày; sai reset về 0. Ngày ôn
hiện theo Date.today của Odoo (khác lịch gửi theo timezone của learner).
Điểm tự trả lời đúng không phải điểm lần thử đầu tiên; chỉ loại câu đã
được lộ đáp án. /hint cung cấp từ vựng/công thức, không gọi AI.

| Lệnh | Hành vi |
| --- | --- |
| /connect CODE | Mã một lần, 10 phút, gắn với bot |
| /start, /help | Hướng dẫn và reply keyboard |
| /lesson | Mở/tiếp tục buổi; không thay câu đang chờ |
| /explain | Từ, cụm từ, ngữ pháp đã có |
| /hint | Gợi ý công thức/từ vựng |
| /answer | Đáp án và giải thích, không tăng ghi nhớ |
| /ask QUESTION | AI giải thích câu hiện tại |
| /skip | Bỏ qua kể cả đang chấm, hủy kết quả cũ, ôn ngày mai |
| /stop | Dừng buổi, hủy job và tin đang chờ; giữ câu chưa xong |
| /pause, /resume | Dừng/bật lại lịch; pause cũng dừng buổi |
| /progress | Tổng số bài đã giao và bài đạt 4 lượt nhớ |
| Tin thường | Đáp án bài tập; khớp chuẩn hóa thì chấm tại chỗ |

/stop tăng command_epoch; job cũ không thể áp kết quả vào buổi mới.
Dừng buổi hôm nay giữ plan chuẩn bị cho ngày mai. /pause dừng cả plan
tương lai; /resume khôi phục đúng slot đó, không tạo thêm bản ghi trùng.
Kết quả /ask chỉ áp dụng khi câu hỏi vẫn là câu hiện tại. Đổi topic/level
hoặc bot trong khi chờ AI cũng làm job cũ bị bỏ qua. Lệnh dừng không thu
hồi được tin đã đến Telegram hoặc HTTP đang gửi ra ngoài.

## 3. Sinh buổi mới mỗi ngày

Bật enabled và daily_ai_enabled (mặc định true cho daily_ai_enabled).
Cron prepare chạy mỗi phút, chuẩn bị buổi hôm nay từ 30 phút trước giờ
học; hỗ trợ cửa sổ qua nửa đêm để chuẩn bị buổi ngày mai. Khi khởi động
sau giờ học, chuẩn bị buổi hôm nay. Không sinh trước nhiều ngày.
Unique (learner_id, daily_date) và khóa learner tránh tạo trùng khi cron
lặp. Mỗi buổi sinh 5 bài liên quan trong một request, gồm 65 field nội dung
phẳng q1_name...q5_answer_explanation_vi. Lộ trình thêm q1_options cho
câu trắc nghiệm (66 field); server quyết định dạng bài, unit và tag lỗi. Có lịch sử bài gần đây trong
prompt; từ chối bài trùng exercise trong batch hoặc 60 bài AI gần nhất.
Đây là chống trùng văn bản chuẩn hóa, không phải so khớp ngữ nghĩa.

Mặc định daily_ai_auto_approve=True cho buổi hằng ngày; có thể tắt để
admin duyệt. require_approval điều khiển tạo bài thủ công, mặc định False
để không cần admin duyệt; có thể bật lại nếu chủ động muốn kiểm duyệt.
Đến giờ, ưu tiên một bài ôn đến hạn nếu có, rồi bài mới trong plan;
buổi vẫn kết thúc sau 5 câu, nên có thể dùng 1 ôn + 4 mới. Nếu không có
bài ôn thì dùng 5 bài mới. Bài chưa dùng có thể được chọn làm dự phòng.
Chuẩn bị không gửi tin trước giờ. Nếu AI chậm/lỗi/hết quota hoặc bài
chưa duyệt, dùng bài ready trong kho. Nếu kho cũng hết, chờ tạo/duyệt.
Hồ sơ còn câu hôm trước: gửi lại câu hoặc báo đang chấm, không im lặng
rồi đánh dấu ngày đã chạy. Lịch gửi dedup theo ngày tại timezone learner.
Buổi stopped không tự mở lại trong ngày; /lesson cho phép học chủ động.
Plan ready/preparing cũ chưa dùng hết hạn sau hơn một ngày; giữ buổi active.

Kho tự do cài sẵn 45 bản ghi: 5 bài ban đầu và 20 tình huống need/can, mỗi tình
huống có bản starter/beginner. Chưa phải 45 tình huống khác nhau hay giáo
trình đầy đủ. Ví dụ đã tách khỏi đáp án. Render lọc dòng ví dụ chứa đáp
án để bảo vệ dữ liệu cũ; generation từ chối ví dụ làm lộ đáp án. Migration
chỉ sửa seed còn nguyên câu mẫu cũ, giữ nội dung người dùng đã chỉnh.

## 4. AI và transaction

Gemini: chọn Interactions (mặc định) hoặc generateContent, API key trong
header. Auto dùng models.list có phân trang, lọc Flash, ưu tiên stable,
không tự chọn Pro; thử tối đa 3 model chỉ khi 404. Interactions store=false,
chỉ nhận completed/model_output, không lấy thought. Legacy chỉ nhận STOP.
9Router: URL mặc định http://localhost:20128/v1, combo daily-english;
POST chat/completions, Bearer key nếu có, stream=false, JSON object,
max_tokens=8192, timeout30s; header tắt token saver. Chỉ nhận finish_reason
stop. Mọi output kiểm tra field/type/độ dài. Chuỗi mỗi field tối đa4000.
Key/token chỉ admin đọc nhưng không mã hóa tại rest; không ghi vào tài liệu.

Job pending/running/done/failed/skipped. Grade ưu tiên hơn generation.
Claim trong transaction ngắn, lưu quota và lease5phút, commit bằng
ir.cron._commit_progress TRƯỚC HTTP. Không giữ khóa learner trong lúc
chờ AI. Sau HTTP kết thúc snapshot, lấy lại khóa và kiểm tra epoch,
lease, trạng thái job/buổi/câu hỏi/bot trước khi áp kết quả. Worker chết
được thu hồi lease; tối đa3 lần thử. Generate/prepare backoff2/4phút; grade/explain thử lại
sau10/20giây, đăng ký cron trigger tại next_run. Lần lỗi đầu của tác vụ
tương tác gửi thông báo chờ, không bắt người học gửi lại câu trả lời. Ngoại lệ dự kiến lưu
error_code gọn, không lưu raw response. Job cũ khi upgrade1.0.7 thiếu
identity bị skipped, câu grading được mở lại; không replay tác vụ cũ.

Quota global theo ngày UTC, đếm lượt claim worker, default30; một lượt
Gemini Auto có thể gồm nhiều HTTP404 fallback. GET models và nút test
admin không tính quota. Hết quota: grade/explain failed, trả câu về
awaiting và thông báo giờ reset; generate/prepare lùi đến đầu ngày UTC.
Người học vẫn dùng hint, đáp án, skip/stop và chấm khớp tại chỗ được.
Token response không hợp lệ chưa đo được. Không tính tiền/quy đổi phí.

## 5. Telegram và tốc độ

Webhook /daily_english/telegram/webhook, POST public, secret header bắt
buộc, private chat có sender ID bằng chat ID. Giới hạn16KB và text2000
ký tự; bỏ qua edited/group/media. Receipt unique(bot_hash,update_id),
khóa theo update và learner; giữ mã receipt để chống replay lâu dài.
Đổi token buộc ghép nối lại. Không dùng chung bot với addon khác.

Outbox phân đoạn3800 UTF-16 units, keyboard ở phần cuối, FIFO mỗi learner.
State pending/sending/sent/failed/skipped; mỗi phần claim/commit trước
HTTP, không giữ khóa learner khi chờ Telegram; checkpoint next_part
được lưu trước phần kế. Thu hồi sending hết lease2phút. /stop hủy pending
và sending; tin đang bay có thể vẫn đến, nhưng không gửi các phần tiếp.
Tối đa5 lỗi, backoff120/240/480/960giây. Không bảo đảm exactly-once nếu
worker chết sau Telegram nhận nhưng trước khi checkpoint commit.

Enqueue đánh thức cron AI phù hợp trực tiếp qua _trigger/NOTIFY sau
commit, song song với delivery. Hai cron AI riêng: grade/explain và
generate/prepare; mỗi cron một job/lượt. CẦN max_cron_threads >=3 để
Telegram, chấm bài và tạo bài có thể chạy đồng thời. Cron một phút là
dự phòng. config/local.conf đã đổi thành3, cần restart. Không có cam kết latency cố định từ API bên ngoài.

## 6. Lưu trữ và dọn dữ liệu

Cron ngày gọi english.session._cron_cleanup. retention_days mặc định60,
0=tắt, tối thiểu7 ngày. Mỗi model tối đa1000 bản ghi/lượt để tránh khóa lâu.
Dọn outbox và job terminal quá hạn, API usage cũ; giữ pending/running/sending.
Dọn attempt đã chấm của bài done/mastered>=4, chỉ khi không còn job tham
chiếu. Giữ tiến độ tổng hợp và mọi bài đã học/cần ôn. Giữ summary buổi
365 ngày, chỉ dọn done/stopped/failed cũ. Bài AI quá hạn chưa học và không
còn plan tham chiếu mới bị xóa. Không xóa seed hoặc mã receipt chống replay.
Xóa dữ liệu tái sử dụng không gian PostgreSQL, không đảm bảo file DB nhỏ
ngay. Không tự VACUUM FULL hay xóa bản sao lưu. Chưa có audio/media.

## 7. Cài và kiểm chứng

Restart Odoo, upgrade daily_english (có migration), kiểm tra cấu hình AI
và Telegram, bật lịch ngày + tạo buổi AI; chọn tự duyệt hoặc duyệt thủ
công. Giữ Odoo/ngrok/9Router chạy. localhost9Router phải truy cập từ WSL.
Xem lịch sử trong Người học → session_ids. Không thử bot thật bằng tests.

Runner WSL:
```bash
/home/lamnv/.pyenv/versions/odoo19-env/bin/python \
  /home/lamnv/code/odoo-19/odoo-bin --config=/dev/null \
  -d daily_english_test_20261008 --db_user=lamnv \
  --addons-path=/home/lamnv/code/odoo-19/addons,project,addons_oca/addons_oca/web \
  --http-port=1389 --max-cron-threads=0 -u daily_english \
  --test-enable --without-demo=all --test-tags=/daily_english \
  --stop-after-init
```

2026-10-11: vòng cuối 76 test methods pass, 0 failed/errors (API mock),
log /tmp/daily_english_hardening_final3.log. Pycodestyle max79 và
git diff --check pass. Upgrade/migration đã chạy trên DB test riêng.
Kiểm tra hai transaction thật trên DB test xác nhận learner row có thể
FOR UPDATE NOWAIT trong lúc gọi AI và gửi Telegram; /stop ở connection
thứ hai commit được, kết quả AI về sau bị bỏ qua. Fixtures đã dọn và
config test đã khôi phục. Chưa đo tốc độ bot/model thật hay upgrade DB
người dùng. Cấu hình local max_cron_threads=2 đã được ghi vào file,
chỉ có hiệu lực sau khi restart tiến trình Odoo.

Tài liệu API:
- https://ai.google.dev/api/interactions-api
- https://ai.google.dev/api/generate-content
- https://github.com/decolua/9router/blob/master/gitbook/content/en/integration/other-tools.md
- https://core.telegram.org/bots/api


## 8. Lộ trình và sổ lỗi sai — 19.0.1.0.8

Học theo lộ trình mặc định bật ở learner.curriculum_enabled; unit_id rỗng
được chọn chặng đầu khi bắt đầu học. Tắt tùy chọn này để dùng kho tự do.
Không xóa tiến độ hoặc thay câu đang chờ của phiên cũ khi nâng cấp.

8 chặng: đại từ + be khẳng định; be phủ định; câu hỏi be; hiện tại đơn
I/you/we/they; hiện tại đơn he/she/it; do/does; can; was/were.
Có menu Lộ trình xem/sửa mục tiêu và công thức từng chặng; hồ sơ Người
học có chặng hiện tại, sổ lỗi sai và chặng của mỗi buổi học.

Chuyển chặng ở ĐẦU BUỔI tiếp theo, không giữa buổi và không khi còn câu
awaiting/grading. Điều kiện: 4 bài khác nội dung được tự làm đúng, trong
đó ít nhất 2 bài dịch/hội thoại. independent_credit lưu trên progress,
không phụ thuộc attempt đã dọn. Sai khi ôn sẽ thu hồi credit bài đó;
đúng không trợ giúp cấp lại. Hint/explain/answer/ask đã trả kết quả đều
là trợ giúp; mở sổ lỗi khi đang làm câu cũng đánh dấu trợ giúp vì có thể
lộ đáp án. Không đếm bản sao cùng exercise nhiều lần. Không tự lùi chặng;
chặng cuối tiếp tục luyện/ôn, không tuyên bố đã thành thạo tiếng Anh.

Mỗi batch mới: choice → cloze → reorder → translate → dialogue. Bài ôn
đến hạn có thể thay một câu; không cam kết mọi buổi luôn đủ cả 5 dạng.
Choice có 2–4 options khác nhau, đáp án là nguyên văn một option; thứ tự
hiển thị xáo ổn định theo lesson ID, không đổi khi thử lại. Nhận A/B/C/D
hoặc nội dung option, chấm ngay cả đáp án sai; ngoài lựa chọn chỉ nhắc
nhập lại, không ghi lỗi. Cloze dùng ___, đáp án là từ/cụm còn thiếu.
Các dạng còn lại trả lời câu hoàn chỉnh. Khớp đáp án chấm tại chỗ; câu
khác gửi AI để chấp nhận cách diễn đạt tương đương và phân loại lỗi.

Bài giới thiệu mục tiêu/công thức ở câu đầu; ví dụ khác với câu kiểm tra.
Đáp án một từ ở choice/cloze được phép xuất hiện trong ví dụ câu khác;
không lọc mất ví dụ chỉ vì nó cũng có từ is/am. Sinh AI vẫn yêu cầu không
chép nguyên câu kiểm tra vào ví dụ. Schema/constraint kiểm cấu trúc,
không chứng minh ngữ pháp hay nội dung do AI sinh là chính xác.

Kho dự phòng lộ trình có 40 bài khác nhau (8 × 5), lưu thành 160 bản ghi
để phục vụ 2 level × 2 topic. Đây là bài nền tảng dùng chung, không phải
160 tình huống khác nhau hay bài dev chuyên sâu. Các bản ghi tĩnh dùng
chung giữa người học. AI sinh bài mới theo level/topic và unit, dựa trên
lịch sử hiện có; không tăng số request mặc định (1 request/batch).

english.mistake gộp theo learner/unit/error_type: lần sai, câu sai và
câu sửa gần nhất, giải thích, ngày và số câu phục hồi. Không tạo một dòng
cho mọi lần sai. Tag cố định: be, pronoun, verb, order, article,
preposition, vocabulary, other. AI không chắc dùng other; choice dùng
tag sẵn của bài. Đây là phân loại hỗ trợ học, có thể cần admin kiểm tra.

Batch hằng ngày dành câu đầu cho lỗi đang mở có nhiều lần mắc nhất ở
chặng hiện tại hoặc trước đó; dùng câu MỚI, không chép câu sai cũ. Các
câu 2–5 theo chặng hiện tại. Bài thủ công chỉ dùng lỗi của chặng hiện tại.
Đúng 2 exercise khác nhau, khác câu gây lỗi gần nhất và không trợ giúp
thì chuyển lỗi sang improving (đã luyện đúng), không gọi là hết lỗi.
Sai lại mở lại và reset lượt phục hồi. Notebook không bị cron retention
xóa; số dòng bị giới hạn theo unit và bộ tag, chỉ giữ ví dụ gần nhất.

Telegram: /roadmap xem chặng và điều kiện chuyển; /mistakes xem tối đa
5 lỗi đang mở gần nhất; /help có cả hai lệnh. Chưa thêm inline buttons,
âm thanh hoặc báo cáo tuần. Reply keyboard hiện có vẫn dùng được.

Job giữ snapshot unit/target_unit/tag. Đổi chặng trước khi kết quả AI về
thì bỏ kết quả cũ. Plan cũ được thay job khi bắt đầu chặng mới; bài cũ
không được trộn vào chặng mới trừ câu ôn có chủ đích. Draft không cùng
unit không chặn tạo bài. Migration 1.0.8 bỏ generation pending/running
thiếu snapshot của người học bật lộ trình, giữ nguyên grade và progress.

Triển khai: restart Odoo rồi upgrade daily_english; trong Người học kiểm
tra Học theo lộ trình và Chặng hiện tại. Gửi /roadmap, sau đó /lesson.
Nếu có bài đang chờ, hoàn thành hoặc /skip để tiếp tục, không mất bài cũ.
Chưa upgrade DB db_lamnv hay gọi AI/Telegram thật trong task này.

Kiểm chứng 1.0.8 ngày 2026-10-11: 98 test methods pass, 0 failed/errors,
log /tmp/daily_english_curriculum_final.log trên DB test riêng, API mock.
Bao gồm worker tạo batch, chấm choice/câu tự viết, chuyển chặng, lỗi ở
chặng trước, credit khi có trợ giúp, migration và ACL notebook. Kiểm tra
PEP 8 max79 và git diff --check pass. security/.gitignore giữ file ACL
ir.model.access.csv trong Git dù quy tắc chung bỏ qua *.csv.


## 9. Sửa chờ chấm bài — 2026-10-11

Chẩn đoán read-only DB thật: job chấm đã nhận, cron/outbox hoạt động,
nhưng API thất bại lần đầu và mã cũ chỉ lưu ai_unavailable_or_invalid.
Một lượt chẩn đoán cùng prompt tới 9Router nhận JSON đúng schema; không
commit DB hay gửi Telegram. Job thật sau đó tự hoàn tất ở lần thử thứ 2.
Không đủ dữ liệu truy ngược lỗi lần đầu là timeout hay output sai.

Bản sửa giữ nguyên tối đa 3 lần, giảm backoff grade/explain xuống10/20s,
trigger cron đúng thời điểm, báo người học ở lần thất bại đầu. Đây là thời
gian lên lịch, không phải cam kết thời gian API/Telegram trả kết quả.
Lưu mã an toàn api_timeout, connection_failed, http_NNN, invalid_response,
invalid_ai_output hoặc invalid_lesson; không lưu raw response/API key.
Không cần đổi schema/version; cần restart tiến trình Odoo để nạp Python.
100 test methods pass, 0 lỗi, /tmp/daily_english_retry_fix.log (API mock,
DB riêng), pycodestyle max79 và git diff --check pass. Chưa restart Odoo
đang chạy; kết quả chấm thật bên trên đến từ cơ chế retry cũ.


## 10. Tối ưu tốc độ — 19.0.1.0.9

Tách cron_english_interactive (grade/explain) khỏi cron_english_jobs
(generate/prepare); migration cập nhật code cron cũ vì XML noupdate.
Enqueue đánh thức đúng cron ngay, không đợi gửi acknowledgement xong.
Outbox vẫn FIFO nên xác nhận luôn trước kết quả. Hết một job đánh thức
các luồng còn việc. Quota dùng chung, khóa claim chỉ trong transaction
ngắn; nếu tranh khóa thì hẹn lại1giây, không chờ cron dự phòng1phút.
Không tạo thread tự quản hoặc gọi mạng trong webhook.

Chấm tại chỗ thêm các viết tắt không mơ hồ: I'm, you're, we're, they're,
isn't, aren't, wasn't, weren't, don't, doesn't, didn't, can't, won't;
chuẩn hóa dấu nháy cong. Không tự mở rộng she's/he's (is hoặc has), không
fuzzy-match tên hay bỏ qua phủ định. Đáp án khác nghĩa vẫn gửi AI.
Tái sử dụng tối đa20 kết quả gần nhất của CÙNG progress/người học, cùng
đáp án chuẩn hóa, sau thời điểm lesson sửa gần nhất; vẫn ghi attempt mới,
áp dụng quy tắc xem đáp án và sổ lỗi. Không chia sẻ cache giữa người học.
Prompt chấm bỏ câu ví dụ lặp, yêu cầu nhận xét tối đa2 câu ngắn240ký tự.
Không giảm giới hạn token vì có thể cắt mất JSON trên model suy luận.

Cần restart + upgrade daily_english để tạo cron riêng và chạy migration.
local.conf đặt max_cron_threads=3; chưa restart/upgrade DB thật trong task.
Không cam kết phản hồi tức thời với câu cần API, không thay model/combo
9Router của người dùng. Tác vụ sinh bài không còn giữ cùng cron với chấm.

Kiểm chứng: 104 test methods pass, 0 failed/errors trên DB riêng và API
mock, log /tmp/daily_english_speed_final.log. Có test luồng chấm hoàn tất
trong khi luồng tạo bài chưa trả về, trigger độc lập, cache riêng và
hết hiệu lực khi sửa bài, dạng viết tắt không bỏ phủ định. Pycodestyle
max79 và git diff --check pass. Chưa đo latency thực tế sau triển khai.


## 11. Tự động duyệt theo yêu cầu người dùng — 2026-10-11

Đã áp dụng trực tiếp db_lamnv bằng ORM: require_approval=False,
daily_ai_auto_approve=True; chuyển 1 bài generated/draft đang chờ sang
ready. Không đổi bài nháp tự viết, không gọi AI hoặc gửi tin Telegram.
Cấu hình có hiệu lực ngay, người học gửi /lesson để tiếp tục. Mặc định
cài mới cũng không yêu cầu duyệt. Message khi chờ sinh bài trong chế độ
tự động không nhắc duyệt nữa (thay Python này cần restart). Giữ validation
nội dung/schema AI trước khi lưu và dùng bài, không coi tự duyệt là bảo
đảm nội dung ngôn ngữ chính xác. Kiểm thử 104 methods pass, 0 failed/errors,
DB riêng + mock API, log /tmp/daily_english_auto.log; pycodestyle và diff
check pass. Thay đổi DB thật bên trên là cấu hình theo yêu cầu, không
phải chạy tests trên DB thật.


## 12. Dự phòng khi hết bài mới — 2026-10-11

Ảnh người dùng cho thấy dừng sau thông báo đang tạo bài. Đọc DB tại thời
điểm báo lỗi: job generate pending sau invalid_ai_output, kho unit hiện
hết bài chưa giao. Chẩn đoán khi tiếp tục: job mới nhất đã done; một lượt
chẩn đoán API riêng gặp lỗi kết nối/phản hồi, rollback, không gửi bot.

Khi hết bài, vẫn xếp tác vụ tạo mới nhưng gửi ngay một câu đã học cùng
unit/level/topic nếu có, không chọn câu hiện tại hoặc câu đã xong trong
buổi này. Gắn answer_shown=True cho lượt ôn sớm để không cộng review_step
hay independent_credit; thông báo rõ là ôn dự phòng. Nếu không có câu
phù hợp vẫn phải chờ AI. Generate phục vụ buổi active dùng retry10/20s
và báo lần lỗi đầu như tác vụ tương tác. Bài mới về không gửi lại câu
đang awaiting/grading. Ưu tiên bài mới trước bài dự phòng ở lần chuyển
câu tiếp. Không thay đổi schema, cần restart Odoo để nạp Python mới.

106 test methods pass, 0 lỗi trên DB riêng, API mock; log
/tmp/english_fallback.log. AST và kiểm tra dòng Python max79, git diff
--check dùng cho vòng này; pycodestyle chưa có trong runtime hiện tại.
Chưa restart tiến trình Odoo thật, chưa đo độ trễ sau bản sửa.


## 13. Nạp menu lệnh Telegram

Cấu hình → Cập nhật menu lệnh Telegram gọi setMyCommands cho scope
all_private_chats, language mặc định và vi, rồi setChatMenuButton với
type commands. Đăng ký15 lệnh đang hỗ trợ kèm mô tả tiếng Việt; ask và
connect hướng dẫn thêm tham số. Chỉ admin được gọi action, cần token,
không cần public_url/webhook để đăng ký menu. Không gửi tin nhắn và
không đổi webhook. Có thể bấm lại để cập nhật; chỉ báo thành công khi
Telegram xác nhận cả3 request. Các thiết lập scope riêng từng chat do
công cụ khác tạo có thể ưu tiên hơn scope all_private_chats.

Restart và upgrade addon để thấy nút mới. Chưa gọi đăng ký trên bot thật
trong task này. Telegram: https://core.telegram.org/bots/api#setmycommands
và https://core.telegram.org/bots/api#setchatmenubutton .


## 14. Giới hạn chờ của tác vụ tương tác

2026-10-11: job24 grade thực tế mất khoảng73giây, thành công lần2;
lượt21/22 thành công lần1 trong3giây. Không truy ngược được mã lỗi đầu
vì thành công đã xóa error_code. Đã bỏ delay retry cho grade/explain:
retry trigger ngay sau commit, tối đa2 lần rồi trả câu về awaiting và
báo lỗi. Context english_job_kind đặt timeout urllib12s cho grade/explain
ở cả Gemini/9Router; tạo bài và nút kiểm tra kết nối giữ30s. Đây là timeout
socket, không phải deadline tổng thời gian hay cam kết bot trả trong24s.
Giảm thời gian chờ có thể khiến model chậm bị báo lỗi sớm hơn; không tự
chấm đúng/sai nếu chưa có kết quả. Generate đang phục vụ buổi active vẫn
retry10/20s, prepare giữ2/4phút. Message phản ánh đúng từng loại retry.
109 tests pass,0failed/errors, DB riêng API mock, log
/tmp/english_fast_retry.log; AST, max79 và git diff --check kiểm tra.
Chưa restart Odoo thật; cần restart để áp dụng, không đổi schema DB.


## 15. Không giới hạn AI nội bộ

Theo yêu cầu dùng cá nhân, daily_api_limit mặc định0=không giới hạn.
Worker chỉ chặn khi limit khác0, vẫn ghi usage. Đã lưu0 trực tiếp vào
config db_lamnv qua ORM, đặt lại next_run của pending bị daily_quota.
CẦN restart Odoo để logic mới hiểu0 là unlimited; chưa restart trong
lượt này. Sau restart gửi lại đáp án bị từ chối. Upgrade để thấy nhãn
mới trong cấu hình. Không đổi giới hạn nhà cung cấp. 110 tests pass,
0failed/errors, DB riêng API mock, /tmp/english_unlimited.log.


## 16. Hội thoại mở — 19.0.1.0.10

Dialogue được chấm theo tính phù hợp của câu trả lời cá nhân, không ép
tên/nơi làm việc/nghề nghiệp theo answer mẫu. Prompt chấm bỏ đáp án mẫu,
ưu tiên thông tin người học. Correct diễn tả đúng ý; grammar_clean phân
biệt lỗi nhỏ cần sửa. Ví dụ I work at company được phép đúng ý, sửa thành
I work at a company. Lặp nguyên câu hỏi không tính trả lời. Các dạng
translate/cloze/reorder/choice không đổi tiêu chí.

Mỗi dialogue có2lượt: câu đầu được chấp nhận thì AI hỏi thêm dựa trên
câu trả lời và kèm nghĩa tiếng Việt. Lưu question/turn/support trên
progress; câu trả lời kế tiếp chấm theo followup, không theo câu gốc.
Lượt đầu chưa cộng buổi/credit; lượt2 hoàn tất thì tính1 bài. Có lỗi nhỏ
hoặc đã hỗ trợ ở một trong2lượt thì không tăng credit ghi nhớ. Câu sai
vẫn sửa và thử lại; /skip,/stop giữ hành vi hiện có. /answer ở followup
(bao gồm nút Đáp án) không đưa đáp án của câu gốc; hướng dẫn dùng /ask.
Không cache hoặc chấm exact cho dialogue vì cần tạo followup và phụ
thuộc câu hỏi đang diễn ra; tối đa2 lượt AI thành công cho bài hội thoại.

Seed dialogue đổi sang câu hỏi cá nhân; migration chỉ sửa khi exercise
vẫn đúng nội dung seed cũ, giữ bài admin đã chỉnh. Bài AI dialogue mới
được yêu cầu không áp đặt vai hoặc thông tin cá nhân. Bài cũ hiển thị
rõ bối cảnh chỉ gợi ý. /ask cũng dùng câu followup hiện tại. Khi giao lại
bài ôn thì reset trạng thái hội thoại. Có trường mới nên cần restart và
upgrade addon; chưa triển khai lên db_lamnv. Chất lượng chấm vẫn phụ
thuộc model, tests không chứng minh mọi câu thực tế đều chấm đúng.

112 tests pass,0failed/errors, DB riêng API mock, log
/tmp/english_dialogue.log. Kiểm AST, giới hạn79ký tự và git diff --check.
