# SPDX-License-Identifier: GPL-3.0-only
"""Translations at the UI boundary; device and controller data stay unchanged."""

import re


LANGUAGE_OPTIONS = (
    ('zh_TW', '繁體中文'),
    ('en', 'English'),
    ('ja', '日本語'),
    ('ko', '한국어'),
)

# Keys are Traditional Chinese UI strings. Values are English, Japanese and Korean.
_TEXT = {
    '手機活動助手': ('Mobile activity assistant', 'モバイル活動アシスタント', '모바일 활동 도우미'),
    'tt tool · 手機活動助手': ('tt tool · Mobile activity assistant', 'tt tool · モバイル活動アシスタント', 'tt tool · 모바일 활동 도우미'),
    '最小化': ('Minimize', '最小化', '최소화'),
    '最大化或還原': ('Maximize or restore', '最大化／元に戻す', '최대화 또는 복원'),
    '關閉視窗': ('Close window', 'ウィンドウを閉じる', '창 닫기'),
    '連接你的手機': ('Connect your phone', 'スマートフォンを接続', '휴대전화를 연결하세요'),
    '開啟 USB 偵錯並允許這台電腦': ('Enable USB debugging and authorize this computer', 'USB デバッグを有効にし、この PC を許可してください', 'USB 디버깅을 켜고 이 컴퓨터를 허용하세요'),
    '選擇手機': ('Select a phone', 'スマートフォンを選択', '휴대전화 선택'),
    '未偵測到手機': ('No phone detected', 'スマートフォンが見つかりません', '휴대전화를 찾을 수 없습니다'),
    '請選擇已授權的裝置並連線。': ('Select an authorized device to connect.', '許可済みの端末を選択して接続してください。', '승인된 기기를 선택하여 연결하세요.'),
    '請確認 USB 資料線、USB 偵錯與授權。': ('Check the USB data cable, USB debugging, and authorization.', 'USB データケーブル、USB デバッグ、端末の許可を確認してください。', 'USB 데이터 케이블, USB 디버깅 및 기기 승인을 확인하세요.'),
    '請選擇已授權的手機。': ('Select an authorized phone.', '許可済みのスマートフォンを選択してください。', '승인된 휴대전화를 선택하세요.'),
    '正在連線手機': ('Connecting to phone', 'スマートフォンに接続中', '휴대전화 연결 중'),
    '正在載入手機畫面。': ('Loading the phone screen.', 'スマートフォンの画面を読み込み中です。', '휴대전화 화면을 불러오는 중입니다.'),
    '重新偵測': ('Scan again', '再検出', '다시 검색'),
    '連線手機': ('Connect', '接続', '연결'),
    '中斷連線': ('Disconnect', '切断', '연결 해제'),
    '等待連線': ('Waiting for connection', '接続待ち', '연결 대기 중'),
    '連線未完成': ('Connection failed', '接続できませんでした', '연결하지 못했습니다'),
    '找不到 FFmpeg。加入 PATH 後重新開啟 tt tool。': ('FFmpeg was not found. Add it to PATH and reopen tt tool.', 'FFmpeg が見つかりません。PATH に追加して tt tool を開き直してください。', 'FFmpeg를 찾을 수 없습니다. PATH에 추가하고 tt tool을 다시 여세요.'),
    '手機已連線': ('Phone connected', 'スマートフォンを接続しました', '휴대전화가 연결되었습니다'),
    '已中斷連線': ('Disconnected', '切断しました', '연결이 해제되었습니다'),
    '連線中斷': ('Connection lost', '接続が切断されました', '연결이 끊겼습니다'),
    '等待手機重新連線': ('Waiting for phone to reconnect', 'スマートフォンの再接続を待機中', '휴대전화 재연결을 기다리는 중'),
    '正在切換模式': ('Switching activity', 'モードを切り替え中', '모드 전환 중'),
    '重新連線手機。': ('Reconnecting to the phone.', 'スマートフォンに再接続しています。', '휴대전화에 다시 연결하는 중입니다.'),
    '正在套用設定並重新連線。': ('Applying settings and reconnecting.', '設定を適用して再接続しています。', '설정을 적용하고 다시 연결하는 중입니다.'),
    '請將手機轉為直向。': ('Rotate the phone to portrait.', 'スマートフォンを縦向きにしてください。', '휴대전화를 세로 방향으로 돌려 주세요.'),
    '畫面已就緒，可以開始探險。': ('Ready to start exploring.', '探検を開始できます。', '탐험을 시작할 수 있습니다.'),
    '畫面已就緒，可以開始釣魚。': ('Ready to start fishing.', '釣りを開始できます。', '낚시를 시작할 수 있습니다.'),
    '即時畫面': ('Live view', 'ライブ画面', '실시간 화면'),
    '即時手機畫面': ('Live phone screen', 'スマートフォンのライブ画面', '휴대전화 실시간 화면'),
    '連線後顯示手機畫面': ('Phone screen appears after connecting', '接続後にスマートフォンの画面を表示', '연결 후 휴대전화 화면이 표시됩니다'),
    '尚無手機畫面': ('No phone image yet', 'スマートフォンの画面はまだありません', '아직 휴대전화 화면이 없습니다'),
    '顯示手機預覽': ('Show phone preview', 'スマートフォンのプレビューを表示', '휴대전화 미리보기 표시'),
    '預覽已關閉': ('Preview off', 'プレビューを非表示', '미리보기 꺼짐'),
    '點擊畫面可放大': ('Click the screen to enlarge', '画面をクリックして拡大', '화면을 클릭하여 확대'),
    '點擊放大即時預覽': ('Click to enlarge the live view', 'クリックしてライブ画面を拡大', '클릭하여 실시간 화면 확대'),
    '放大手機預覽': ('Enlarge phone preview', 'スマートフォンのプレビューを拡大', '휴대전화 미리보기 확대'),
    '釣魚': ('Fishing', '釣り', '낚시'),
    '探險': ('exploring', '探検', '탐험'),
    '遺跡探險': ('Ruins adventure', '遺跡探検', '유적 탐험'),
    '釣魚控制': ('Fishing', '釣り', '낚시'),
    '開始釣魚': ('Start fishing', '釣りを開始', '낚시 시작'),
    '暫停釣魚': ('Pause fishing', '釣りを一時停止', '낚시 일시정지'),
    '繼續釣魚': ('Resume fishing', '釣りを再開', '낚시 계속'),
    '開始探險': ('Start exploring', '探検を開始', '탐험 시작'),
    '暫停探險': ('Pause exploring', '探検を一時停止', '탐험 일시정지'),
    '繼續探險': ('Resume exploring', '探検を再開', '탐험 계속'),
    '開始': ('Start', '開始', '시작'),
    '暫停': ('Pause', '一時停止', '일시정지'),
    '繼續': ('Resume', '再開', '계속'),
    '結束': ('End', '終了', '종료'),
    '結束  Esc': ('End  Esc', '終了  Esc', '종료  Esc'),
    '已暫停': ('Paused', '一時停止中', '일시정지됨'),
    '已結束': ('Ended', '終了しました', '종료됨'),
    '工作階段已停止': ('Session stopped', 'セッションを停止しました', '작업이 중지되었습니다'),
    '自動釣魚中': ('Auto fishing', '自動釣り中', '자동 낚시 중'),
    '畫面已確認，重新下鉤': ('Screen confirmed; retrying cast', '画面を確認し、再度投入します', '화면 확인 후 다시 던지는 중'),
    '畫面已確認，重新拉鉤': ('Screen confirmed; retrying hook', '画面を確認し、再度引きます', '화면 확인 후 다시 낚는 중'),
    '等待畫面穩定後重試': ('Waiting for a stable screen before retrying', '画面が安定してから再試行します', '화면이 안정되면 다시 시도합니다'),
    '畫面未確認，持續等待': ('Waiting for screen recognition', '画面を確認するまで待機中', '화면 확인을 기다리는 중'),
    '等待上鉤，持續確認畫面': ('Waiting for a bite and checking the screen', 'アタリを待ちながら画面を確認中', '입질을 기다리며 화면 확인 중'),
    '重新確認判定畫面': ('Rechecking the timing screen', '判定画面を再確認中', '타이밍 화면을 다시 확인 중'),
    '自動探險中': ('Auto exploring', '自動探検中', '자동 탐험 중'),
    '戰鬥結果': ('Battle result', '戦闘結果', '전투 결과'),
    '開啟寶箱': ('Opening chest', '宝箱を開封', '상자 열기'),
    '遊戲錯誤提示': ('Game error dialog', 'ゲームのエラー表示', '게임 오류 안내'),
    '正在確認遊戲錯誤提示': ('Confirming the game error', 'ゲームのエラーを確認中', '게임 오류 확인 중'),
    '觀察測試中 · 不點擊': ('Observing · no taps', '観察中 · タップなし', '관찰 중 · 터치하지 않음'),
    '持續釣魚': ('Continuous fishing', '連続釣り', '연속 낚시'),
    '依設定上限停止': ('Stop at configured limits', '設定した上限で停止', '설정한 한도에서 중지'),
    '標準操作': ('Standard input', '標準操作', '기본 조작'),
    '模擬手動操作': ('Simulate manual input', '手動操作を再現', '수동 조작 모방'),
    '下鉤': ('Casts', '投入', '던지기'),
    '結算': ('Results', '結果', '결과'),
    '已開始': ('Started', '開始', '시작'),
    '已完成': ('Completed', '完了', '완료'),
    '設定': ('Settings', '設定', '설정'),
    '語言': ('Language', '言語', '언어'),
    '設定模式': ('Setup mode', '設定モード', '설정 모드'),
    '自動學習': ('Automatic learning', '自動学習', '자동 학습'),
    '手動設定': ('Manual setup', '手動設定', '수동 설정'),
    '自動學習模式': ('Automatic learning mode', '自動学習モード', '자동 학습 모드'),
    '手動設定模式': ('Manual setup mode', '手動設定モード', '수동 설정 모드'),
    '自動會依畫面調整': ('Automatically adjusts to the screen', '画面に合わせて自動調整', '화면에 맞춰 자동 조정'),
    '自動依畫面調整操作位置': ('Automatically adjusts touch positions to the screen', '画面に合わせてタップ位置を自動調整', '화면에 맞춰 터치 위치를 자동 조정'),
    '手動按拖曳位置操作': ('Uses the touch positions you drag into place', 'ドラッグで指定した位置をタップ', '드래그하여 지정한 위치를 터치'),
    '目前模式恢復預設': ('Restore defaults for this mode', '現在のモードを初期設定に戻す', '현재 모드 기본값 복원'),
    '儲存並立即套用': ('Save and apply now', '保存してすぐに適用', '저장 후 즉시 적용'),
    '儲存後立即套用': ('Applied immediately after saving', '保存後すぐに適用されます', '저장 후 즉시 적용됩니다'),
    '設定已儲存並套用。': ('Settings saved and applied.', '設定を保存して適用しました。', '설정을 저장하고 적용했습니다.'),
    '設定已儲存，連線後套用。': ('Settings saved; they will apply after connecting.', '設定を保存しました。接続後に適用されます。', '설정을 저장했습니다. 연결 후 적용됩니다.'),
    '兩個模式的設定各自儲存': ('Settings are saved separately for each mode', '各モードの設定は個別に保存されます', '각 모드의 설정은 별도로 저장됩니다'),
    '兩種模式各自保留設定': ('Each mode keeps its own settings', '各モードの設定はそれぞれ保持されます', '각 모드는 설정을 별도로 유지합니다'),
    '設定  ↗': ('Settings  ↗', '設定  ↗', '설정  ↗'),
    '調整畫面、操作位置與活動設定': ('Adjust the screen, touch points and activity settings', '画面・タップ位置・アクティビティを設定', '화면, 터치 위치 및 활동 설정 조정'),
    '設定已儲存；結束後下次開始時套用。': ('Settings saved; they apply after ending and starting again.', '設定を保存しました。終了後、次回開始時に適用されます。', '설정을 저장했습니다. 종료 후 다시 시작할 때 적용됩니다.'),
    '設定  ＋': ('Settings  +', '設定  ＋', '설정  ＋'),
    '收合設定  −': ('Hide settings  −', '設定を閉じる  −', '설정 접기  −'),
    '展開釣魚模式、畫面範圍與進階設定': ('Open fishing, screen and advanced settings', '釣り・画面範囲・詳細設定を開く', '낚시, 화면 범위 및 고급 설정 열기'),
    '釣魚設定': ('Fishing settings', '釣りの設定', '낚시 설정'),
    '遺跡探險設定': ('Ruins settings', '遺跡探検の設定', '유적 탐험 설정'),
    '畫面與操作位置': ('Screen and touch positions', '画面とタップ位置', '화면 및 터치 위치'),
    '拖曳角落調整遊戲範圍，拖曳圓點調整觸控位置': ('Drag the corners to adjust the game area; drag a dot to set its touch position', '角をドラッグしてゲーム範囲を調整し、点をドラッグしてタップ位置を設定', '모서리를 끌어 게임 영역을 조절하고 점을 끌어 터치 위치를 설정하세요'),
    '拖曳角落與圓點': ('Drag corners and markers', '角とマーカーをドラッグ', '모서리와 표시점을 드래그'),
    '釣魚按鈕': ('Fishing button', '釣りボタン', '낚시 버튼'),
    '入口': ('Entrance', '入口', '입구'),
    '前進': ('Advance', '前進', '전진'),
    '寶藏': ('Treasure', '宝物', '보물'),
    '戰鬥': ('Fight', '戦闘', '전투'),
    '撤離': ('Retreat', '撤退', '철수'),
    '保守撤離': ('Retreat as a precaution', '安全のため撤退', '안전을 위해 철수'),
    '探險策略': ('Adventure strategy', '探検の方針', '탐험 전략'),
    '一般寶藏勝率門檻': ('Normal treasure win-rate threshold', '通常の宝物の勝率しきい値', '일반 보물 승률 기준'),
    '紅色寶藏勝率門檻': ('Red treasure win-rate threshold', '赤い宝物の勝率しきい値', '빨간 보물 승률 기준'),
    '連點間隔（秒）': ('Tap interval (seconds)', '連続タップ間隔（秒）', '연속 터치 간격 (초)'),
    '最多連點次數': ('Maximum taps', '最大タップ回数', '최대 터치 횟수'),
    '遊戲範圍': ('Game area', 'ゲーム範囲', '게임 영역'),
    '觸控位置': ('Touch position', 'タップ位置', '터치 위치'),
    '還原畫面範圍': ('Reset screen area', '画面範囲をリセット', '화면 영역 초기화'),
    '重設自動校正': ('Reset auto calibration', '自動補正をリセット', '자동 보정 초기화'),
    '將重設自動校正': ('Auto calibration will be reset', '自動補正をリセットします', '자동 보정이 초기화됩니다'),
    '勝率低於門檻時撤離': ('Retreat when win rate is below the threshold', '勝率がしきい値を下回ると撤退', '승률이 기준보다 낮으면 철수'),
    '完整螢幕': ('Full screen', '画面全体', '전체 화면'),
    '完整螢幕  ·  點擊位置可在下方調整': ('Full screen · Adjust the touch point below', '画面全体 · タップ位置を下で調整できます', '전체 화면 · 아래에서 터치 위치 조절'),
    '已設定遊戲範圍': ('Game area set', 'ゲーム範囲を設定済み', '게임 영역 설정됨'),
    '設定遊戲範圍與按鈕': ('Set game area and button', 'ゲーム範囲とボタンを設定', '게임 영역 및 버튼 설정'),
    '設定遊戲範圍與按鈕  ↗': ('Set game area and button  ↗', 'ゲーム範囲とボタンを設定  ↗', '게임 영역 및 버튼 설정  ↗'),
    '拖曳完整遊戲範圍': ('Drag over the full game area', 'ゲーム画面全体をドラッグ', '게임 화면 전체를 드래그하세요'),
    '點選釣魚與收下共用按鈕': ('Select the shared fishing and claim button', '釣りと受け取りの共通ボタンを選択', '낚시와 수령에 사용하는 공통 버튼을 선택하세요'),
    '釣魚模式': ('Fishing mode', '釣りモード', '낚시 모드'),
    '遊戲畫面與點擊': ('Game screen and touch', 'ゲーム画面とタップ', '게임 화면 및 터치'),
    '按鈕 X': ('Button X', 'ボタン X', '버튼 X'),
    '按鈕 Y': ('Button Y', 'ボタン Y', '버튼 Y'),
    '釣魚上限': ('Fishing limits', '釣りの上限', '낚시 한도'),
    '下鉤上限': ('Cast limit', '投入回数の上限', '던지기 횟수 한도'),
    '時間上限（分鐘）': ('Time limit (minutes)', '時間制限（分）', '시간 한도 (분)'),
    '持續釣魚開啟時，不受這些上限限制': ('These limits do not apply while continuous fishing is on', '連続釣りがオンの場合、これらの上限は適用されません', '연속 낚시가 켜져 있으면 이 한도가 적용되지 않습니다'),
    '持續釣魚開啟時，上限不生效': ('Limits are disabled during continuous fishing', '連続釣り中は上限が適用されません', '연속 낚시 중에는 한도가 적용되지 않습니다'),
    '進階時序': ('Advanced timing', '詳細タイミング', '고급 타이밍'),
    '觸控延遲補償（毫秒）': ('Touch latency compensation (ms)', 'タップ遅延の補正（ミリ秒）', '터치 지연 보정 (ms)'),
    '串流延遲估計（毫秒）': ('Estimated stream latency (ms)', '配信遅延の推定（ミリ秒）', '스트림 지연 추정 (ms)'),
    '時序不確定餘量（毫秒）': ('Timing uncertainty margin (ms)', 'タイミングの不確実性（ミリ秒）', '타이밍 불확실성 여유 (ms)'),
    '辨識間隔（秒）': ('Recognition interval (seconds)', '認識間隔（秒）', '인식 간격 (초)'),
    '收下首次等待（秒）': ('Initial claim delay (seconds)', '受け取りまでの待機（秒）', '첫 수령 대기 시간 (초)'),
    '收下重試間隔（秒）': ('Claim retry interval (seconds)', '受け取り再試行間隔（秒）', '수령 재시도 간격 (초)'),
    '修改會在下次開始時套用': ('Changes apply the next time you start', '変更は次回開始時に適用されます', '변경 사항은 다음 시작 시 적용됩니다'),
    '修改會在結束後下次開始釣魚時套用': ('Changes apply after ending and starting fishing again', '終了後、次に釣りを開始すると変更が適用されます', '종료 후 낚시를 다시 시작하면 변경 사항이 적용됩니다'),
    '還原已儲存設定': ('Restore saved settings', '保存済みの設定に戻す', '저장된 설정 복원'),
    '恢復預設值': ('Restore defaults', '初期値に戻す', '기본값 복원'),
    '儲存設定': ('Save settings', '設定を保存', '설정 저장'),
    '取消': ('Cancel', 'キャンセル', '취소'),
    '關閉': ('Close', '閉じる', '닫기'),
    '重新框選': ('Select again', '選択し直す', '다시 선택'),
    '已還原上次儲存的設定。': ('Restored saved settings.', '保存済みの設定に戻しました。', '저장된 설정을 복원했습니다.'),
    '已恢復預設值；開始釣魚時套用。': ('Defaults restored; they apply when fishing starts.', '初期値に戻しました。釣りの開始時に適用されます。', '기본값을 복원했습니다. 낚시를 시작할 때 적용됩니다.'),
    '已選擇遊戲範圍與按鈕，開始釣魚時套用。': ('Game area and button set; they apply when fishing starts.', 'ゲーム範囲とボタンを設定しました。釣りの開始時に適用されます。', '게임 영역과 버튼을 설정했습니다. 낚시를 시작할 때 적용됩니다.'),
    '選擇 adb.exe': ('Choose adb.exe', 'adb.exe を選択', 'adb.exe 선택'),
    '所有檔案': ('All files', 'すべてのファイル', '모든 파일'),
    'ADB (adb.exe);;所有檔案 (*)': ('ADB (adb.exe);;All files (*)', 'ADB (adb.exe);;すべてのファイル (*)', 'ADB (adb.exe);;모든 파일 (*)'),
    '等待前景驗證': ('Checking the foreground app', '前面のアプリを確認中', '포그라운드 앱 확인 중'),
    '等待遊戲恢復前景': ('Waiting for the game to return to foreground', 'ゲームが前面に戻るのを待機中', '게임이 포그라운드로 돌아오기를 기다리는 중'),
    '畫面延遲，等待新畫面恢復': ('Frame delayed; waiting for a fresh frame', '画面が遅延しています。新しいフレームを待機中', '화면이 지연되어 새 프레임을 기다리는 중'),
    '等待連續移動樣本；停幀或方向不明時不點擊': ('Waiting for motion samples; no tap while frozen or direction is unknown', '連続した動きを待機中。停止中や方向不明時はタップしません', '연속 움직임을 기다리는 중이며 화면이 멈추거나 방향을 모르면 터치하지 않습니다'),
    '黃條窗口小於截圖時序誤差，本趟略過': ('Yellow-bar window is shorter than timing uncertainty; skipping this pass', '黄色の判定時間が時刻誤差より短いため、今回は見送ります', '노란 막대 구간이 타이밍 오차보다 짧아 이번에는 건너뜁니다'),
    '勝率尚未確認，持續辨識中': ('Checking the win rate', '勝率を確認しています', '승률을 계속 확인하고 있습니다'),
    '寶藏類型尚未確認，持續辨識中': ('Checking the treasure type', '宝物の種類を確認しています', '보물 종류를 계속 확인하고 있습니다'),
    '勝率讀值互相矛盾，持續辨識中': ('Win rate readings disagree; checking again', '勝率の読取結果が一致しないため再確認中', '승률 판독값이 달라 다시 확인 중입니다'),
    '未能確認勝率，正在戰鬥': ('Win rate unclear; fighting', '勝率を確認できないため戦闘中', '승률을 확인할 수 없어 전투 중입니다'),
    '勝率尚未確認，稍後自動戰鬥': ('Win rate unclear; fighting shortly', '勝率を確認できない場合は戦闘します', '승률 미확인 시 잠시 후 전투합니다'),
    '寶藏類型尚未確認，稍後自動戰鬥': ('Treasure type unclear; fighting shortly', '宝物の種類を確認できない場合は戦闘します', '보물 종류 미확인 시 잠시 후 전투합니다'),
    '勝率讀值互相矛盾，稍後自動戰鬥': ('Win rate readings disagree; fighting shortly', '勝率の読取結果が不一致のため戦闘します', '승률 판독값이 달라 잠시 후 전투합니다'),
    '勝率未辨明': ('win rate unclear', '勝率不明', '승률 불명'),
    '遺跡入口': ('Ruins entrance', '遺跡の入口', '유적 입구'),
    '探險中': ('Exploring', '探検中', '탐험 중'),
    '發現寶藏': ('Treasure found', '宝物を発見', '보물 발견'),
    '遭遇首領': ('Boss encounter', 'ボスに遭遇', '보스 조우'),
    '探險結算': ('Adventure results', '探検結果', '탐험 결과'),
    '抵達遺跡新區域': ('New ruins area reached', '遺跡の新エリアに到達', '유적의 새 구역에 도착'),
    '等待畫面確認': ('Waiting for screen confirmation', '画面の確認を待機中', '화면 확인 대기 중'),
    '準備下鉤': ('Ready to cast', '投入準備', '던지기 준비'),
    '等待上鉤': ('Waiting for a bite', 'アタリ待ち', '입질 대기'),
    '需要拉鉤': ('Reel in', '引き上げ', '낚싯대 당기기'),
    '黃條判定': ('Timing bar', 'タイミング判定', '타이밍 막대'),
    '結果展示': ('Showing result', '結果表示', '결과 표시'),
    '未確認畫面': ('Unrecognized screen', '未確認の画面', '확인되지 않은 화면'),
    '觀察中': ('Observing', '観察中', '관찰 중'),
    '達到本次運行時長上限': ('Session time limit reached', '今回の実行時間の上限に達しました', '이번 작업의 시간 한도에 도달했습니다'),
    '畫面長時間無法確認，已暫停；檢查遮擋、彈窗和框選範圍': ('Screen unrecognized for too long; paused. Check overlays and game area.', '画面を長時間確認できないため一時停止しました。重なりや選択範囲を確認してください。', '화면을 오래 확인하지 못해 일시정지했습니다. 가림과 선택 영역을 확인하세요.'),
    '等待連續幀確認': ('Waiting for consecutive frames', '連続フレームを確認中', '연속 프레임 확인 중'),
    '按鍵後畫面未進入下一階段，已暫停；請檢查空格映射': ('Screen did not advance after input; paused. Check the key mapping.', '入力後に次の画面に進まないため一時停止しました。キー割り当てを確認してください。', '입력 후 다음 단계로 이동하지 않아 일시정지했습니다. 키 매핑을 확인하세요.'),
    '已按鍵，等待階段變化': ('Input sent; waiting for the next stage', '入力済み。次の段階を待機中', '입력 완료. 다음 단계 대기 중'),
    '等待上鉤逾時，已暫停': ('Bite wait timed out; paused', 'アタリ待ちがタイムアウトしたため一時停止しました', '입질 대기 시간이 초과되어 일시정지했습니다'),
    '等待魚上鉤': ('Waiting for a bite', 'アタリを待機中', '입질 대기 중'),
    '達到下鉤次數上限': ('Cast limit reached', '投入回数の上限に達しました', '던지기 횟수 한도에 도달했습니다'),
    '初始畫面已確認，下鉤一次': ('Ready screen confirmed; casting', '開始画面を確認し、投入します', '시작 화면 확인 후 던지는 중'),
    '上鉤提示已確認，拉鉤一次': ('Bite confirmed; reeling in', 'アタリを確認し、引き上げます', '입질 확인 후 당기는 중'),
    '等待結果動畫': ('Waiting for result animation', '結果アニメーションを待機中', '결과 애니메이션 대기 중'),
    '等待結果頁關閉': ('Waiting for results to close', '結果画面が閉じるのを待機中', '결과 화면이 닫히기를 기다리는 중'),
    '結果頁持續可見，嘗試空格關閉': ('Results still visible; retrying close', '結果画面が表示中のため、再度閉じます', '결과 화면이 계속 보여 닫기를 다시 시도합니다'),
    '等待畫面穩定': ('Waiting for a stable screen', '画面が安定するのを待機中', '화면이 안정되기를 기다리는 중'),
    '判定階段逾時，已暫停': ('Timing stage timed out; paused', '判定がタイムアウトしたため一時停止しました', '타이밍 단계 시간이 초과되어 일시정지했습니다'),
    '判定條或浮標暫未識別': ('Timing bar or marker not recognized', '判定バーまたはマーカーを認識できません', '타이밍 막대 또는 표시기를 인식하지 못했습니다'),
    '等待浮標離開黃條，確認完整目標邊界': ('Waiting for the marker to leave the target to confirm its bounds', 'マーカーが黄色の範囲から出て境界を確認するのを待機中', '표시기가 노란 구간을 벗어나 경계를 확인하기를 기다리는 중'),
    '偵測到下一輪變化，重新估計速度': ('Next round detected; estimating speed again', '次の判定を検出し、速度を再推定中', '다음 판정을 감지하여 속도를 다시 추정 중'),
    '按鍵後未確認下一輪，已暫停': ('Next round not confirmed after input; paused', '入力後に次の判定を確認できないため一時停止しました', '입력 후 다음 판정을 확인하지 못해 일시정지했습니다'),
    '本輪已觸發，等待黃條變化或浮標復位': ('Input sent; waiting for the next target', '入力済み。次の判定を待機中', '입력 완료. 다음 목표 대기 중'),
    '按鍵間隔保護': ('Waiting for input cooldown', '入力間隔を待機中', '입력 간격 대기 중'),
    '估計浮標速度': ('Estimating marker speed', 'マーカーの速度を推定中', '표시기 속도 추정 중'),
    '截圖處理延遲過高，本幀跳過': ('Frame processing delayed; skipping frame', 'フレーム処理の遅延が大きいためスキップします', '프레임 처리 지연이 커서 건너뜁니다'),
    '黃條過窄或速度不穩定，等待更可靠的機會': ('Target too narrow or speed unstable; waiting', '判定範囲が狭いか速度が不安定なため待機します', '목표가 너무 좁거나 속도가 불안정하여 기다립니다'),
    '預測生效位置位於黃條安全範圍': ('Predicted touch falls inside the safe target', '予測タップ位置が安全な範囲内です', '예측 터치 위치가 안전한 범위 안에 있습니다'),
    '等待浮標進入可命中範圍': ('Waiting for marker to enter the target', 'マーカーが判定範囲に入るのを待機中', '표시기가 목표 범위에 들어오기를 기다리는 중'),
    '找不到 ADB；請選擇 Android platform-tools 的 adb.exe': ('ADB not found; select adb.exe from Android platform-tools', 'ADB が見つかりません。Android platform-tools の adb.exe を選択してください', 'ADB를 찾을 수 없습니다. Android platform-tools의 adb.exe를 선택하세요'),
    'ADB 工作階段已關閉': ('ADB session closed', 'ADB セッションは終了しています', 'ADB 세션이 종료되었습니다'),
    '請明確選擇一台手機': ('Select a phone', 'スマートフォンを選択してください', '휴대전화를 선택하세요'),
    'ADB 指令失敗': ('ADB command failed', 'ADB コマンドが失敗しました', 'ADB 명령 실패'),
    'ADB 回應逾時；請檢查 USB 連線與手機授權': ('ADB timed out; check USB connection and phone authorization', 'ADB がタイムアウトしました。USB 接続と端末の許可を確認してください', 'ADB 응답 시간이 초과되었습니다. USB 연결과 휴대전화 승인을 확인하세요'),
    '手機未傳回有效 PNG 截圖': ('The phone did not return a valid PNG screenshot', 'スマートフォンから有効な PNG を取得できませんでした', '휴대전화에서 유효한 PNG 스크린샷을 받지 못했습니다'),
    '手機截圖無法解碼': ('Could not decode phone screenshot', 'スマートフォンのスクリーンショットを読み込めません', '휴대전화 스크린샷을 디코딩할 수 없습니다'),
    '手機方向已改變；請轉回直向後重新連線': ('Phone orientation changed; return to portrait and reconnect', '画面の向きが変わりました。縦向きに戻して再接続してください', '휴대전화 방향이 변경되었습니다. 세로로 돌린 후 다시 연결하세요'),
    '手機方向或解析度改變，請重新連線': ('Phone orientation or resolution changed; reconnect', '画面の向きまたは解像度が変わりました。再接続してください', '화면 방향 또는 해상도가 변경되었습니다. 다시 연결하세요'),
    '手機方向或解析度改變；請重新連線並框選': ('Phone orientation or resolution changed; reconnect and select the area', '画面の向きまたは解像度が変わりました。再接続して範囲を選択してください', '화면 방향 또는 해상도가 변경되었습니다. 다시 연결하고 영역을 선택하세요'),
    '無法確認手機前景 App；請解鎖並開啟遊戲': ('Cannot verify the foreground app; unlock the phone and open the game', '前面のアプリを確認できません。端末のロックを解除してゲームを開いてください', '포그라운드 앱을 확인할 수 없습니다. 잠금을 해제하고 게임을 여세요'),
    '找不到 FFmpeg；請安裝 FFmpeg 並加入 PATH 後重新連線': ('FFmpeg not found; install it, add it to PATH, and reconnect', 'FFmpeg が見つかりません。インストールして PATH に追加し、再接続してください', 'FFmpeg를 찾을 수 없습니다. 설치 후 PATH에 추가하고 다시 연결하세요'),
    '影像串流結束；請重新連線': ('Video stream ended; reconnect', '映像ストリームが終了しました。再接続してください', '영상 스트림이 종료되었습니다. 다시 연결하세요'),
    '舊影像串流無法停止，請重新連線': ('Could not stop the old stream; reconnect', '以前のストリームを停止できません。再接続してください', '이전 스트림을 중지할 수 없습니다. 다시 연결하세요'),
    '遺跡探險辨識資源缺失': ('Ruins recognition assets are missing', '遺跡の認識データがありません', '유적 인식 파일이 없습니다'),
    '請設定有效的完整遊戲範圍': ('Set a valid game area', '有効なゲーム範囲を設定してください', '유효한 게임 영역을 설정하세요'),
    '遊戲範圍超出手機畫面': ('Game area exceeds the phone screen', 'ゲーム範囲がスマートフォン画面を超えています', '게임 영역이 휴대전화 화면을 벗어납니다'),
    '遊戲選區太小；請框選完整遊戲': ('Selected game area is too small; select the entire game', '選択範囲が小さすぎます。ゲーム画面全体を選択してください', '선택 영역이 너무 작습니다. 게임 화면 전체를 선택하세요'),
    'humanize 必須為布林值': ('Manual input simulation must be on or off', '手動操作の再現をオンまたはオフにしてください', '수동 조작 모방을 켜거나 꺼야 합니다'),
    'continuous 必須為布林值': ('Continuous fishing must be on or off', '連続釣りをオンまたはオフにしてください', '연속 낚시를 켜거나 꺼야 합니다'),
    '下鉤上限必須為整數': ('The cast limit must be a whole number', '投入回数の上限は整数にしてください', '던지기 횟수 한도는 정수여야 합니다'),
    '按壓時間超出範圍': ('Press duration is out of range', '押す時間が範囲外です', '누르기 시간이 허용 범위를 벗어났습니다'),
    '未取得前景 App': ('Could not determine foreground app', '前面のアプリを取得できません', '포그라운드 앱을 확인할 수 없습니다'),
    '圖片編碼失敗': ('Image encoding failed', '画像のエンコードに失敗しました', '이미지 인코딩에 실패했습니다'),
    '截圖尺寸無效': ('Invalid screenshot dimensions', 'スクリーンショットのサイズが無効です', '스크린샷 크기가 유효하지 않습니다'),
    '手機預覽畫面格式無效': ('Invalid phone preview format', 'スマートフォンのプレビュー形式が無効です', '휴대전화 미리보기 형식이 유효하지 않습니다'),
    '畫面設定模式無效': ('Invalid screen setup mode', '画面設定モードが無効です', '화면 설정 모드가 유효하지 않습니다'),
    '畫面設定內容無效': ('Invalid screen setup settings', '画面設定の内容が無効です', '화면 설정 내용이 유효하지 않습니다'),
    '遺跡按鈕位置無效': ('Invalid ruins button positions', '遺跡ボタンの位置が無効です', '유적 버튼 위치가 유효하지 않습니다'),
}


_ALIASES = {
    '准备下钩': '準備下鉤', '等待上钩': '等待上鉤', '需要拉钩': '需要拉鉤',
    '黄条判定': '黃條判定', '结果展示': '結果展示', '未确认画面': '未確認畫面',
    '观察中': '觀察中', '达到本次运行时长上限': '達到本次運行時長上限',
    '画面长时间无法确认，已暂停；检查遮挡、弹窗和框选范围': '畫面長時間無法確認，已暫停；檢查遮擋、彈窗和框選範圍',
    '等待连续帧确认': '等待連續幀確認',
    '按键后画面未进入下一阶段，已暂停；请检查空格映射': '按鍵後畫面未進入下一階段，已暫停；請檢查空格映射',
    '已按键，等待阶段变化': '已按鍵，等待階段變化',
    '等待上钩超时，已暂停': '等待上鉤逾時，已暫停', '等待上鉤超時，已暫停': '等待上鉤逾時，已暫停', '等待鱼上钩': '等待魚上鉤',
    '达到下钩次数上限': '達到下鉤次數上限', '初始画面已确认，下钩一次': '初始畫面已確認，下鉤一次',
    '上钩提示已确认，拉钩一次': '上鉤提示已確認，拉鉤一次', '等待结果动画': '等待結果動畫',
    '等待结果页关闭': '等待結果頁關閉', '结果页持续可见，尝试空格关闭': '結果頁持續可見，嘗試空格關閉',
    '等待画面稳定': '等待畫面穩定', '判定阶段超时，已暂停': '判定階段逾時，已暫停', '判定階段超時，已暫停': '判定階段逾時，已暫停',
    '判定条或浮标暂未识别': '判定條或浮標暫未識別',
    '等待浮标离开黄条，确认完整目标边界': '等待浮標離開黃條，確認完整目標邊界',
    '检测到下一轮变化，重新估计速度': '偵測到下一輪變化，重新估計速度', '檢測到下一輪變化，重新估計速度': '偵測到下一輪變化，重新估計速度',
    '按键后未确认下一轮，已暂停': '按鍵後未確認下一輪，已暫停',
    '本轮已触发，等待黄条变化或浮标复位': '本輪已觸發，等待黃條變化或浮標復位',
    '按键间隔保护': '按鍵間隔保護', '估计浮标速度': '估計浮標速度',
    '截图处理延迟过高，本帧跳过': '截圖處理延遲過高，本幀跳過',
    '黄条过窄或速度不稳定，等待更可靠的机会': '黃條過窄或速度不穩定，等待更可靠的機會',
    '预测生效位置位于黄条安全范围': '預測生效位置位於黃條安全範圍',
    '等待浮标进入可命中范围': '等待浮標進入可命中範圍',
    '图片编码失败': '圖片編碼失敗', '图片编码失敗': '圖片編碼失敗',
    '截图尺寸无效': '截圖尺寸無效',
}

_PREFIXES = {
    'ADB 輸入結果未確認，持續確認畫面：': ('ADB input unconfirmed; checking the screen: ', 'ADB 入力が未確認です。画面を確認中：', 'ADB 입력 결과 미확인. 화면 확인 중: '),
    'ADB 輸入結果未確認，等待畫面確認：': ('ADB input unconfirmed; checking the screen: ', 'ADB 入力が未確認です。画面を確認中：', 'ADB 입력 결과 미확인. 화면 확인 중: '),
    '前景確認中，暫停輸入：': ('Checking foreground; input paused: ', '前面のアプリを確認中。入力を停止：', '포그라운드 확인 중. 입력 일시정지: '),
    '前景驗證持續失敗，已暫停：': ('Foreground verification failed; paused: ', '前面のアプリを確認できず一時停止：', '포그라운드를 확인하지 못해 일시정지: '),
    '遺跡辨識資源無法載入：': ('Could not load ruins recognition assets: ', '遺跡の認識データを読み込めません：', '유적 인식 파일을 불러올 수 없습니다: '),
    '辨識資源無法載入：': ('Could not load recognition assets: ', '認識データを読み込めません：', '인식 파일을 불러올 수 없습니다: '),
    '探險工作階段停止：': ('Adventure session stopped: ', '探検セッションを停止しました：', '탐험 작업이 중지되었습니다: '),
    '工作階段停止：': ('Session stopped: ', 'セッションを停止しました：', '작업이 중지되었습니다: '),
    '前景 App：': ('Foreground app: ', '前面のアプリ：', '포그라운드 앱: '),
}


def _language(language):
    return language if language in ('zh_TW', 'en', 'ja', 'ko') else 'zh_TW'


def translate(text, language='zh_TW'):
    """Translate a UI message while preserving unknown details and identifiers.

    Traditional Chinese is the source language. The result is always a string;
    callers may translate template strings before applying ``str.format``.
    """
    if text is None:
        return ''
    text = str(text)
    language = _language(language)
    text = _ALIASES.get(text, text)
    if language == 'zh_TW':
        waiting = re.fullmatch(r'画面未确认，已等待\s*(\d+)秒(?:／([\d.]+)秒|（不自动超时）)?', text)
        if waiting:
            elapsed, limit = waiting.groups()
            suffix = f'／{limit}秒' if limit else ('（不自動逾時）' if text.endswith('（不自动超时）') else '')
            return f'畫面未確認，已等待{elapsed}秒{suffix}'
        return text
    index = {'en': 0, 'ja': 1, 'ko': 2}[language]
    if text in _TEXT:
        return _TEXT[text][index]

    # Formatting stays outside translatable values so percentages, decimals and
    # device names are never localized by guesswork.
    reconnect = re.fullmatch(r'影像串流中斷，正在重連（第\s*(\d+)\s*次）', text)
    if reconnect:
        n = reconnect.group(1)
        return (f'Stream interrupted; reconnecting (attempt {n})',
                f'映像が途切れたため再接続中（{n} 回目）',
                f'영상이 끊겨 다시 연결 중 ({n}회차)')[index]

    summary = re.fullmatch(r'總勝率低於\s*(\d+)%\s*撤離\s*·\s*紅色寶藏門檻\s*(\d+)%', text)
    if summary:
        normal, red = summary.groups()
        return (f'Retreat below {normal}% · Red treasure: {red}%',
                f'勝率 {normal}% 未満で撤退 · 赤い宝物は {red}%',
                f'승률 {normal}% 미만 철수 · 빨간 보물 기준 {red}%')[index]

    odds = re.fullmatch(r'(紅色寶藏\s*·\s*)?勝率\s*(\d+)%(?:\s*\+\s*(\d+)%)?\s*=\s*(\d+)%\s*·\s*(撤離|戰鬥)（門檻\s*(\d+)%）', text)
    if odds:
        red, base, bonus, total, choice, threshold = odds.groups()
        prefix = (('Red treasure · ', '赤い宝物 · ', '빨간 보물 · ')[index] if red else '')
        calculated = f'{base}%' + (f' + {bonus}%' if bonus else '') + f' = {total}%'
        action = translate(choice, language)
        return prefix + (f'Win rate {calculated} · {action} (threshold {threshold}%)',
                         f'勝率 {calculated} · {action}（基準 {threshold}%）',
                         f'승률 {calculated} · {action} (기준 {threshold}%)')[index]

    recent = re.fullmatch(r'最近首領\s*(\d+%|勝率未辨明)\s*·\s*(戰鬥|撤離|保守撤離)', text)
    if recent:
        value, choice = recent.groups()
        if value == '勝率未辨明':
            value = translate(value, language)
        action = translate(choice, language)
        return (f'Last boss: {value} · {action}', f'直近のボス：{value} · {action}', f'최근 보스: {value} · {action}')[index]

    waiting = re.fullmatch(r'[畫画]面未[確确][認认]，[已]等待\s*(\d+)秒(?:／([\d.]+)秒|（不自[動动][逾超]時）|（不自[動动]超时）)?', text)
    if waiting:
        elapsed, limit = waiting.groups()
        suffix = f' / {limit}s' if limit else ''
        return (f'Screen unconfirmed; waited {elapsed}s{suffix}',
                f'画面未確認。{elapsed} 秒待機{suffix}',
                f'화면 미확인. {elapsed}초 대기{suffix}')[index]

    metrics = re.fullmatch(r'擷取\s*([\d.]+)\s*fps\s*·\s*辨識\s*([\d.]+)\s*fps\s*·\s*預覽\s*([\d.]+)\s*fps\s*·\s*畫面年齡\s*([\d.]+)\s*ms', text)
    if metrics:
        capture, recognition, preview, age = metrics.groups()
        return (f'Capture {capture} fps · Recognition {recognition} fps · Preview {preview} fps · Frame age {age} ms',
                f'取得 {capture} fps · 認識 {recognition} fps · プレビュー {preview} fps · フレーム経過 {age} ms',
                f'캡처 {capture} fps · 인식 {recognition} fps · 미리보기 {preview} fps · 프레임 경과 {age} ms')[index]

    foreground = re.fullmatch(r'持續確認手機前景為\s*(.+)，已暫停', text)
    if foreground:
        package = foreground.group(1)
        return (f'Foreground app remains {package}; paused',
                f'前面のアプリが {package} のため一時停止',
                f'포그라운드 앱이 {package}이므로 일시정지')[index]

    invalid = re.fullmatch(r'([a-zA-Z_][a-zA-Z_0-9]*) 應介於 ([\d.]+) 與 ([\d.]+)', text)
    if invalid:
        key, low, high = invalid.groups()
        return (f'{key} must be between {low} and {high}',
                f'{key} は {low}～{high} にしてください',
                f'{key} 값은 {low}에서 {high} 사이여야 합니다')[index]

    integer = re.fullmatch(r'([a-zA-Z_][a-zA-Z_0-9]*) 必須為整數', text)
    if integer:
        key = integer.group(1)
        return (f'{key} must be a whole number',
                f'{key} は整数にしてください',
                f'{key} 값은 정수여야 합니다')[index]

    point = re.fullmatch(r'遺跡按鈕 ([A-Z_]+) 位置無效', text)
    if point:
        key = point.group(1)
        return (f'Invalid position for ruins button {key}',
                f'遺跡ボタン {key} の位置が無効です',
                f'유적 버튼 {key} 위치가 유효하지 않습니다')[index]

    for source, values in _PREFIXES.items():
        if text.startswith(source):
            return values[index] + translate(text[len(source):], language)

    # Preserve segment separation for composite UI labels without translating
    # IDs, error payloads or arbitrary text character-by-character.
    if ' · ' in text:
        parts = text.split(' · ')
        return ' · '.join(translate(part.strip(), language) for part in parts)
    return text
