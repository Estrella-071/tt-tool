# SPDX-License-Identifier: GPL-3.0-only
"""Localization of real UI messages, dynamic status and device identifiers."""

import unittest
from fisher.i18n import LANGUAGE_OPTIONS, translate


class LocalizationTests(unittest.TestCase):
    def test_available_languages_and_traditional_chinese_default(self):
        self.assertEqual([code for code, _ in LANGUAGE_OPTIONS], ['zh_TW', 'en', 'ja', 'ko'])
        self.assertEqual(translate('釣魚'), '釣魚')
        self.assertEqual(translate('未确认画面', 'zh_TW'), '未確認畫面')
        self.assertEqual(translate('画面未确认，已等待12秒（不自动超时）', 'zh_TW'),
                         '畫面未確認，已等待12秒（不自動逾時）')

    def test_activity_controls_and_visual_settings_have_all_languages(self):
        source = (
            '釣魚', '遺跡探險', '開始釣魚', '暫停釣魚', '繼續探險', '結束  Esc',
            '釣魚設定', '遺跡探險設定', '畫面與操作位置',
            '拖曳角落調整遊戲範圍，拖曳圓點調整觸控位置', '尚無手機畫面',
            '釣魚按鈕', '入口', '前進', '寶藏', '結算', '戰鬥', '撤離', '戰鬥結果', '開啟寶箱',
            '畫面已確認，重新下鉤', '畫面已確認，重新拉鉤', '等待畫面穩定後重試',
            '畫面未確認，持續等待', '等待上鉤，持續確認畫面', '重新確認判定畫面',
            '探險策略', '一般寶藏勝率門檻', '紅色寶藏勝率門檻',
            '連點間隔（秒）', '最多連點次數', '釣魚上限', '下鉤上限',
            '時間上限（分鐘）', '進階時序', '觸控延遲補償（毫秒）',
            '串流延遲估計（毫秒）', '時序不確定餘量（毫秒）', '辨識間隔（秒）',
            '收下首次等待（秒）', '收下重試間隔（秒）', '恢復預設值',
            '取消', '儲存設定', '持續釣魚', '模擬手動操作',
            '修改會在下次開始時套用', '遊戲範圍', '觸控位置', '還原畫面範圍',
            '重設自動校正', '將重設自動校正', '勝率低於門檻時撤離',
            '設定  ↗', '調整畫面、操作位置與活動設定', '設定已儲存；結束後下次開始時套用。',
            '語言', '拖曳角落與圓點',
            '自動學習', '手動設定', '自動學習模式', '手動設定模式', '自動會依畫面調整',
            '自動依畫面調整操作位置', '手動按拖曳位置操作', '目前模式恢復預設',
            '儲存並立即套用', '兩個模式的設定各自儲存',
            '設定模式', '兩種模式各自保留設定',
            '儲存後立即套用', '設定已儲存並套用。', '設定已儲存，連線後套用。',
            '畫面設定模式無效', '畫面設定內容無效', '遺跡按鈕位置無效',
        )
        for text in source:
            for lang in ('en', 'ja', 'ko'):
                with self.subTest(text=text, lang=lang):
                    translated = translate(text, lang)
                    self.assertTrue(translated)
                    if lang == 'en':
                        self.assertNotEqual(translated, text)

    def test_live_odds_and_thresholds_preserve_values(self):
        for lang in ('en', 'ja', 'ko'):
            self.assertNotEqual(translate('勝率尚未確認，持續辨識中', lang), '勝率尚未確認，持續辨識中')
            self.assertNotEqual(translate('寶藏類型尚未確認，持續辨識中', lang), '寶藏類型尚未確認，持續辨識中')
            self.assertNotEqual(translate('勝率讀值互相矛盾，持續辨識中', lang), '勝率讀值互相矛盾，持續辨識中')
            self.assertNotEqual(translate('勝率尚未確認，稍後自動戰鬥', lang), '勝率尚未確認，稍後自動戰鬥')
            self.assertNotEqual(translate('寶藏類型尚未確認，稍後自動戰鬥', lang), '寶藏類型尚未確認，稍後自動戰鬥')
            self.assertNotEqual(translate('勝率讀值互相矛盾，稍後自動戰鬥', lang), '勝率讀值互相矛盾，稍後自動戰鬥')
        status = '紅色寶藏 · 勝率 30% + 5% = 35% · 戰鬥（門檻 30%）'
        for lang in ('en', 'ja', 'ko'):
            with self.subTest(lang=lang):
                rendered = translate(status, lang)
                for number in ('30%', '5%', '35%'):
                    self.assertIn(number, rendered)
                self.assertNotIn('紅色寶藏', rendered)
                self.assertNotIn('戰鬥', rendered)
        self.assertIn('Fight', translate(status, 'en'))
        self.assertIn('35%', translate('總勝率低於 45% 撤離  ·  紅色寶藏門檻 35%', 'ja'))
        self.assertIn('Retreat', translate('最近首領 勝率未辨明 · 保守撤離', 'en'))

    def test_dynamic_errors_and_device_ids(self):
        source = 'ADB 輸入結果未確認，持續確認畫面：ADB 回應逾時；請檢查 USB 連線與手機授權'
        self.assertIn('timed out', translate(source, 'en'))
        self.assertNotIn('逾時', translate(source, 'en'))
        source = '持續確認手機前景為 com.example.game，已暫停'
        for lang in ('en', 'ja', 'ko'):
            self.assertIn('com.example.game', translate(source, lang))
        self.assertEqual(translate('持續確認手機前景為   com.example.game ，已暫停', 'en'),
                         'Foreground app remains com.example.game; paused')
        self.assertEqual(translate('持續確認手機前景為 ，已暫停', 'en'),
                         '持續確認手機前景為 ，已暫停')
        self.assertIn('12', translate('影像串流中斷，正在重連（第 12 次）', 'en'))
        self.assertIn('whole number', translate('ruins_tap_max 必須為整數', 'en'))
        self.assertIn('FIGHT', translate('遺跡按鈕 FIGHT 位置無效', 'ja'))
        self.assertEqual(translate('unknown: com.example.game', 'ja'), 'unknown: com.example.game')

    def test_counters_metrics_and_simplified_controller_messages(self):
        self.assertEqual(translate('等待上钩超时，已暂停', 'zh_TW'), '等待上鉤逾時，已暫停')
        self.assertNotEqual(translate('等待上钩超时，已暂停', 'en'), '等待上钩超时，已暂停')
        self.assertIn('12s', translate('画面未确认，已等待12秒／60秒', 'en'))
        metrics = '擷取 59.7 fps  ·  辨識 58.6 fps  ·  預覽 55.2 fps  ·  畫面年齡 61 ms'
        english = translate(metrics, 'en')
        for value in ('59.7', '58.6', '55.2', '61'):
            self.assertIn(value, english)
        self.assertIn('Capture', english)

    def test_unknown_language_and_empty_text_have_safe_fallbacks(self):
        self.assertEqual(translate('釣魚', 'unknown'), '釣魚')
        self.assertEqual(translate(None, 'en'), '')
        self.assertEqual(translate('', 'ko'), '')
        self.assertEqual(translate('語言 · 한국어', 'en'), 'Language · 한국어')
        self.assertEqual(translate('語言 · English', 'ja'), '言語 · English')


if __name__ == '__main__':
    unittest.main()
