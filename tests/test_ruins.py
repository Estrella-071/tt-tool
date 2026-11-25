# SPDX-License-Identifier: GPL-3.0-only
"""Ruins recognition and decisions using cropped, anonymous game fixtures."""
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import threading
import time
import numpy as np
import cv2
from fisher.ruins import RuinsController, RuinsDetector, RuinsObservation

FIXTURES = Path(__file__).parent / 'assets' / 'ruins'


class RuinsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = RuinsDetector()

    def image(self, name):
        return cv2.imread(str(FIXTURES / (name+'.png')))

    def test_actual_screen_states_and_base_percentage(self):
        for name, state, chance in [('lobby','LOBBY',None), ('advance','ADVANCE',None),
                ('reward','REWARD',None), ('boss90','BOSS',95), ('boss90_bonus_stream','BOSS',95), ('boss80','BOSS',80), ('boss80_stream','BOSS',80), ('boss80_bonus_stream','BOSS',85), ('boss70_bonus_stream','BOSS',75), ('boss55_bonus_stream','BOSS',60), ('boss55_bonus8_stream','BOSS',63), ('boss30_bonus_stream','BOSS',35), ('boss25_bonus8_stream','BOSS',33), ('boss20_stream','BOSS',20), ('boss20_bonus8_stream','BOSS',28),
                ('boss45','BOSS',50), ('boss50_red','BOSS',50), ('milestone','MILESTONE',None), ('claim','CLAIM',None), ('victory','UNKNOWN',None)]:
            with self.subTest(name=name):
                obs=self.detector.detect(self.image(name))
                self.assertEqual((obs.state,obs.chance),(state,chance))

    def test_boss_boundary_uses_base_chance_and_will_not_guess(self):
        below=self.image('boss45'); other=self.image('boss90')
        below[706:724,261:269]=other[706:724,261:269]
        self.assertEqual(self.detector.detect(below).chance,45)
        obscured=self.image('boss45');obscured[706:724,250:284]=0
        obs=self.detector.detect(obscured)
        self.assertEqual((obs.state,obs.chance),('BOSS',None))
        for chance,expected in ((44,'RETREAT'),(45,'FIGHT'),(90,'FIGHT'),(None,None)):
            controller=RuinsController();obs=RuinsObservation('BOSS',chance,.95)
            self.assertIsNone(controller.observe(obs,10));self.assertIsNone(controller.observe(obs,10.1))
            if chance == 44:
                for t in (10.2,10.4,10.6,10.79):self.assertIsNone(controller.observe(obs,t))
                self.assertEqual(controller.observe(obs,10.9),expected)
            else:
                self.assertEqual(controller.observe(obs,10.2),expected)

    def test_bonus_is_added_and_red_treasure_lowers_threshold(self):
        normal=self.detector.detect(self.image('boss45'))
        self.assertEqual((normal.base,normal.bonus,normal.chance),(45,5,50))
        stream=self.detector.detect(self.image('boss80_bonus_stream'))
        self.assertEqual((stream.base,stream.bonus,stream.chance),(80,5,85))
        without=self.detector.detect(self.image('boss50_red'))
        self.assertEqual((without.base,without.bonus,without.chance,without.red),(50,0,50,True))
        weak=self.detector.detect(self.image('boss20_stream'))
        self.assertTrue(weak.red or weak.red_uncertain)
        red35=self.detector.detect(self.image('boss30_bonus_stream'))
        self.assertEqual((red35.chance,red35.red),(35,True))
        live_case=RuinsController()
        live_case.observe(red35,1.);live_case.observe(red35,1.1)
        self.assertEqual(live_case.observe(red35,1.2),'FIGHT')
        red28=self.detector.detect(self.image('boss20_bonus8_stream'))
        self.assertEqual((red28.base,red28.bonus,red28.chance),(20,8,28))
        self.assertTrue(red28.red or red28.red_uncertain)
        low_case=RuinsController();low_case.observe(red28,1.);low_case.observe(red28,1.1)
        self.assertEqual(low_case.observe(red28,1.2),'RETREAT')
        ctrl=RuinsController()
        for t in (1.,1.1):self.assertIsNone(ctrl.observe(without,t))
        self.assertEqual(ctrl.observe(without,1.2),'FIGHT')
        # Red rewards remain protected by the lower threshold for this round.
        for chance,expected in ((29,'RETREAT'),(30,'FIGHT'),(35,'FIGHT'),(44,'FIGHT')):
            c=RuinsController();c.valuable=True
            later=RuinsObservation('BOSS',chance,.9,chance,0,False)
            c.observe(later,2.);c.observe(later,2.1)
            self.assertEqual(c.observe(later,2.2),expected)
        ordinary=RuinsController();odds=RuinsObservation('BOSS',35,.9,30,5,False)
        ordinary.observe(odds,2.);ordinary.observe(odds,2.1)
        for t in (2.2,2.4,2.6,2.79):self.assertIsNone(ordinary.observe(odds,t))
        self.assertEqual(ordinary.observe(odds,2.9),'RETREAT')
        c=RuinsController();c.commit('CLAIM',4);c.valuable=True
        for t in (5.,5.1,5.2):c.observe(RuinsObservation('LOBBY'),t)
        self.assertFalse(c.valuable)

    def test_bonus_must_be_fully_read_if_plus_is_visible(self):
        damaged=self.image('boss45');damaged[706:724,300:324]=0
        obs=self.detector.detect(damaged)
        self.assertEqual(obs.state,'BOSS');self.assertIsNone(obs.chance)
        missing_plus=self.image('boss45');missing_plus[706:724,289:294]=0
        self.assertIsNone(self.detector.detect(missing_plus).chance)

    def test_milestone_waits_until_banner_clears_without_full_retry_delay(self):
        c=RuinsController();c.commit('ADVANCE',10.)
        banner=RuinsObservation('MILESTONE')
        for t in (10.5,10.6,10.7):self.assertIsNone(c.observe(banner,t))
        advance=RuinsObservation('ADVANCE')
        for t in (11.,11.1):self.assertIsNone(c.observe(advance,t))
        self.assertEqual(c.observe(advance,11.2),'ADVANCE')

    def test_wait_for_confirmation_and_limit_repeated_actions(self):
        controller=RuinsController({'humanize':False,'ruins_tap_interval':.12,'ruins_tap_max':2});obs=RuinsObservation('ADVANCE')
        self.assertIsNone(controller.observe(obs,10));self.assertIsNone(controller.observe(obs,10.1))
        self.assertEqual(controller.observe(obs,10.2),'ADVANCE')
        controller.commit('ADVANCE',10.2)
        for t in (10.5,10.8,11.4,13.,15.1):self.assertIsNone(controller.observe(obs,t))
        self.assertEqual(controller.observe(obs,15.3),'ADVANCE')

    def test_chest_batch_and_confirmation_are_single_spaced_actions(self):
        detector = RuinsDetector(adaptive=False)
        batch = detector.detect(self.image('chest_batch'))
        final = detector.detect(self.image('chest_confirm'))
        self.assertEqual((batch.state, final.state), ('CHEST', 'CHEST'))
        for obs in (batch, final):
            self.assertAlmostEqual(obs.target[0], .5, delta=.02)
            self.assertAlmostEqual(obs.target[1], .912, delta=.025)
        c = RuinsController()
        c.valuable = c.possible_valuable = True
        c.commit('ADVANCE', 1.)
        for t in (2., 2.1):
            self.assertIsNone(c.observe(batch, t))
        self.assertEqual(c.observe(batch, 2.2), 'CHEST')
        c.commit('CHEST', 2.2)
        for t in (2.4, 2.5, 2.6, 3., 4., 5.):
            self.assertIsNone(c.observe(final, t))
        self.assertEqual(c.observe(final, 5.3), 'CHEST')
        c.commit('CHEST', 5.3)
        self.assertTrue(c.valuable)
        self.assertTrue(c.possible_valuable)
        for t in (6.3, 6.4):
            self.assertIsNone(c.observe(RuinsObservation('ADVANCE'), t))
        self.assertEqual(c.observe(RuinsObservation('ADVANCE'), 6.5), 'ADVANCE')
        missing_target = RuinsController()
        for t in (10., 10.1, 10.2, 11.):
            self.assertIsNone(missing_target.observe(RuinsObservation('CHEST'), t))

    def test_chest_button_maps_back_through_calibrated_viewport(self):
        for name, expected_x in (('chest_confirm', .501), ('chest_split', .736)):
            image = self.image(name)
            shifted = cv2.warpAffine(image, np.float32([[1, 0, 12.6], [0, 1, 16]]), (360, 800))
            bordered = cv2.copyMakeBorder(shifted, 0, 0, 45, 45, cv2.BORDER_CONSTANT)
            detector = RuinsDetector(offset=(.035, .02))
            detector.viewport = (.1, .8)
            detector._frame_number = 1
            obs = detector.detect(bordered)
            with self.subTest(name=name):
                self.assertEqual(obs.state, 'CHEST')
                self.assertAlmostEqual(obs.target[0], .1 + .8*(expected_x + .035), delta=.01)
                self.assertAlmostEqual(obs.target[1], .912 + .02, delta=.01)

    def test_chest_split_targets_open_all_and_obeys_retry_interval(self):
        obs = RuinsDetector(adaptive=False).detect(self.image('chest_split'))
        self.assertEqual(obs.state, 'CHEST')
        self.assertAlmostEqual(obs.target[0], .736, delta=.025)
        self.assertAlmostEqual(obs.target[1], .912, delta=.025)
        c = RuinsController()
        for t in (1., 1.1):
            self.assertIsNone(c.observe(obs, t))
        self.assertEqual(c.observe(obs, 1.2), 'CHEST')
        c.commit('CHEST', 1.2)
        for t in (1.4, 2., 3., 4.1):
            self.assertIsNone(c.observe(obs, t))
        self.assertEqual(c.observe(obs, 4.3), 'CHEST')

    def test_chest_tap_uses_detected_position_without_applying_offset_twice(self):
        from fisher.ruins_runtime import RuinsRunner
        from fisher.adb import Frame
        from adb_app import PHONE_DEFAULTS
        with patch('fisher.phone_runtime.Adb'):
            runner = RuinsRunner('adb', 'test', dict(PHONE_DEFAULTS, humanize=False), (2670,1200), 'com.game')
        runner.observe_only = False; runner.active.set(); runner.foreground_ok = True
        now = time.perf_counter(); runner.foreground_at = now
        frame = Frame(np.zeros((800,360,3), dtype=np.uint8), now, now, .02, 1)
        runner._ruins_tap(RuinsController(), 'CHEST', frame, (0,0,360,800),
                          offset=(.1,.1), viewport=(.1,.8), target=(.53,.91))
        x, y = runner.adb.tap.call_args.args
        self.assertAlmostEqual(x, .53*1200, places=3)
        self.assertAlmostEqual(y, .91*2670, places=3)

    def test_expedition_lobby_recognition_never_needs_title_or_button_text(self):
        for glyph in ('A','START','GAME','GO'):
            image=self.image('lobby');image[:200,:]=0
            # Localized button labels can vary in length and glyph shape.
            image[699:716,168:244]=(15,155,230)
            cv2.putText(image,glyph,(170,713),cv2.FONT_HERSHEY_SIMPLEX,.42,(255,255,255),1,cv2.LINE_AA)
            d=RuinsDetector()
            for _ in range(20):obs=d.detect(image)
            self.assertEqual(obs.state,'LOBBY',glyph)

    def test_compressed_stream_lobby_uses_distinct_nontext_geometry(self):
        image=self.image('lobby_stream')
        self.assertEqual(RuinsDetector().detect(image).state,'LOBBY')
        # The fixture removes all title and player information; vary the
        # label region while keeping the graphical control intact.
        for glyph in ('A','START','GAME','GO'):
            changed=image.copy();changed[699:716,168:244]=(15,155,230)
            cv2.putText(changed,glyph,(170,713),cv2.FONT_HERSHEY_SIMPLEX,.42,(255,255,255),1,cv2.LINE_AA)
            self.assertEqual(RuinsDetector().detect(changed).state,'LOBBY',glyph)
        for region in ((112,670,158,713),(238,640,290,675),(165,682,260,729)):
            negative=image.copy();x1,y1,x2,y2=region;negative[y1:y2,x1:x2]=0
            self.assertNotEqual(RuinsDetector().detect(negative).state,'LOBBY',region)
        for name in ('advance','reward','claim','boss45','milestone','victory','error_dialog'):
            self.assertNotEqual(RuinsDetector().detect(self.image(name)).state,'LOBBY',name)
        for path in FIXTURES.parent.glob('*.png'):
            self.assertNotEqual(RuinsDetector().detect(cv2.imread(str(path))).state,'LOBBY',path.name)

    def test_lobby_with_purple_multiplier_badge_survives_stream_and_offsets(self):
        from fisher.ruins_geometry import RuinsGeometry
        image = self.image('lobby_multiplier_stream')
        self.assertEqual(RuinsDetector().detect(image).state, 'LOBBY')
        for quality in (60, 85, 100):
            ok, encoded = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, quality])
            self.assertTrue(ok)
            compressed = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
            for dx, dy in ((0, 0), (-15, -20), (15, 20)):
                shifted = cv2.warpAffine(compressed, np.float32([[1,0,dx],[0,1,dy]]), (360,800))
                offset = RuinsGeometry().locate(shifted, 'LOBBY')
                with self.subTest(quality=quality, dx=dx, dy=dy):
                    self.assertIsNotNone(offset)
                    self.assertAlmostEqual(offset[0], dx/360, delta=.015)
                    self.assertAlmostEqual(offset[1], dy/800, delta=.015)
        no_badge = image.copy(); no_badge[640:675, 238:290] = 0
        self.assertNotEqual(RuinsDetector().detect(no_badge).state, 'LOBBY')
        for path in FIXTURES.glob('*.png'):
            if path.stem not in ('lobby', 'lobby_stream', 'lobby_multiplier_stream'):
                self.assertNotEqual(RuinsDetector(adaptive=False).detect(self.image(path.stem)).state,
                                    'LOBBY', path.name)
        for name in ('advance', 'boss45', 'chest_split', 'chest_confirm', 'error_dialog'):
            for dx, dy in ((0, 0), (-12, 15), (12, -15)):
                shifted = cv2.warpAffine(self.image(name), np.float32([[1,0,dx],[0,1,dy]]), (360,800))
                ok, encoded = cv2.imencode('.jpg', shifted, [cv2.IMWRITE_JPEG_QUALITY, 75])
                self.assertTrue(ok)
                changed = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
                with self.subTest(name=name, dx=dx, dy=dy):
                    self.assertNotEqual(RuinsDetector(adaptive=False).detect(changed).state, 'LOBBY')

    def test_error_dialog_detects_nontext_signals_and_real_button_center(self):
        from fisher.ruins_geometry import error_dialog_target
        image=self.image('error_dialog');target=error_dialog_target(image)
        self.assertIsNotNone(target)
        self.assertAlmostEqual(target[0],.5,delta=.01)
        self.assertAlmostEqual(target[1],.643,delta=.01)
        for dx,dy in ((20,-35),(-20,30),(0,0)):
            moved=cv2.warpAffine(image,np.float32([[1,0,dx],[0,1,dy]]),(360,800),borderValue=(0,0,0))
            target=error_dialog_target(moved)
            self.assertIsNotNone(target)
            self.assertAlmostEqual(target[0],(.5+dx/360),delta=.015)
            self.assertAlmostEqual(target[1],(.643+dy/800),delta=.015)
        for top,bottom in ((40,40),(0,80),(80,0)):
            taller=cv2.copyMakeBorder(image,top,bottom,0,0,cv2.BORDER_CONSTANT,value=(0,0,0))
            self.assertIsNotNone(error_dialog_target(taller))
        d=RuinsDetector();obs=d.detect(image)
        self.assertEqual(obs.state,'ERROR');self.assertIsNotNone(obs.target)

    def test_error_dialog_does_not_assume_text_or_match_choice_panels(self):
        from fisher.ruins_geometry import error_dialog_target
        image=self.image('error_dialog');hsv=cv2.cvtColor(image,cv2.COLOR_BGR2HSV)
        mask=cv2.bitwise_or(cv2.inRange(hsv,(0,90,90),(12,255,255)),cv2.inRange(hsv,(170,90,90),(179,255,255)))
        changed=image.copy();changed[mask>0]=(240,252,252)
        cv2.putText(changed,'ALERT 66',(85,411),cv2.FONT_HERSHEY_SIMPLEX,.65,(90,90,210),2,cv2.LINE_AA)
        self.assertIsNotNone(error_dialog_target(changed))
        blank=image.copy();blank[mask>0]=(240,252,252)
        self.assertIsNone(error_dialog_target(blank))
        choice=image.copy();cv2.rectangle(choice,(20,495),(90,530),(70,210,100),-1)
        self.assertIsNone(error_dialog_target(choice))
        for name in ('advance','lobby','reward','claim','boss45','milestone','victory'):
            self.assertIsNone(error_dialog_target(self.image(name)),name)

    def test_error_confirmation_is_single_with_bounded_backoff(self):
        d=RuinsDetector();obs=d.detect(self.image('error_dialog'));c=RuinsController({'humanize':False})
        c.observe(obs,1.);c.observe(obs,1.1)
        self.assertEqual(c.observe(obs,1.2),'ERROR');c.commit('ERROR',1.2)
        self.assertIsNone(c.observe(obs,2.))
        self.assertEqual(c.observe(obs,9.3),'ERROR');c.commit('ERROR',9.3)
        self.assertIsNone(c.observe(obs,18.))
        self.assertEqual(c.observe(obs,39.4),'ERROR')

    def test_single_tap_waits_after_unknown_or_state_transition(self):
        c=RuinsController({'humanize':False});obs=RuinsObservation('ADVANCE')
        for t in (1.,1.1):c.observe(obs,t)
        self.assertEqual(c.observe(obs,1.2),'ADVANCE');c.commit('ADVANCE',1.2)
        self.assertIsNone(c.observe(RuinsObservation('UNKNOWN'),1.3))
        for t in (1.7,1.8,2.):self.assertIsNone(c.observe(obs,t))
        reward=RuinsObservation('REWARD')
        for t in (2.1,2.2):self.assertIsNone(c.observe(reward,t))
        self.assertEqual(c.observe(reward,2.3),'REWARD')

    def test_boss_cannot_reverse_decision_on_conflicting_odds(self):
        c=RuinsController();fight=RuinsObservation('BOSS',50);retreat=RuinsObservation('BOSS',20)
        c.observe(fight,1.);c.observe(fight,1.1)
        self.assertEqual(c.observe(fight,1.2),'FIGHT');c.commit('FIGHT',1.2)
        for t in (2.,2.1,2.2,5.,9.1):self.assertIsNone(c.observe(retreat,t))
        c.observe(retreat,9.2);c.observe(retreat,9.3)
        self.assertIsNone(c.observe(retreat,9.4))
        self.assertTrue(c.odds_conflict)
        for t in (10.,10.1,10.2):c.observe(RuinsObservation('REWARD'),t)
        for t in (10.3,10.4):self.assertIsNone(c.observe(retreat,t))
        self.assertEqual(c.observe(retreat,10.5),'RETREAT')

    def test_transient_screens_do_not_change_round_counts_or_reset_retry(self):
        c=RuinsController();c.commit('CLAIM',1.);c.valuable=True
        c.observe(RuinsObservation('LOBBY'),2.)
        self.assertEqual(c.completed,0);self.assertTrue(c.claim_latched);self.assertTrue(c.valuable)
        c.observe(RuinsObservation('UNKNOWN'),2.1)
        for t in (3.,3.1,3.2):c.observe(RuinsObservation('LOBBY'),t)
        self.assertEqual(c.completed,1);self.assertFalse(c.claim_latched);self.assertFalse(c.valuable)
        c=RuinsController();c.commit('LOBBY',4.)
        c.observe(RuinsObservation('ADVANCE'),5.)
        c.observe(RuinsObservation('BOSS',80),5.1)
        self.assertEqual(c.started,0);self.assertTrue(c.lobby_latched)
        c.observe(RuinsObservation('UNKNOWN'),5.2)
        for t in (6.,6.1,6.2):c.observe(RuinsObservation('ADVANCE'),t)
        self.assertEqual(c.started,1);self.assertFalse(c.lobby_latched)
        c=RuinsController();c.commit('ADVANCE',10.)
        c.observe(RuinsObservation('CLAIM'),10.3)
        for t in (10.4,10.5,11.):self.assertIsNone(c.observe(RuinsObservation('ADVANCE'),t))

    def test_configured_withdraw_thresholds_use_total_odds(self):
        for red,chance,expected in ((False,49,'RETREAT'),(False,50,'FIGHT'),
                                    (True,34,'RETREAT'),(True,35,'FIGHT')):
            c=RuinsController({'ruins_normal_threshold':50,'ruins_red_threshold':35})
            obs=RuinsObservation('BOSS',chance,.9,chance-5,5,red)
            c.observe(obs,1.);c.observe(obs,1.1)
            if not red and chance == 49:
                for t in (1.2,1.4,1.6,1.79):self.assertIsNone(c.observe(obs,t))
                self.assertEqual(c.observe(obs,1.9),expected)
            else:
                self.assertEqual(c.observe(obs,1.2),expected)

    def test_weak_red_and_fractional_alignment_never_misclassify_red_as_normal(self):
        from dataclasses import replace
        for name in ('boss20_stream', 'boss20_bonus8_stream'):
            for quality in (50,75,90,100):
                image=self.image(name)
                ok,encoded=cv2.imencode('.jpg',image,[int(cv2.IMWRITE_JPEG_QUALITY),quality])
                self.assertTrue(ok)
                obs=RuinsDetector(offset=(0,-.001875)).detect(cv2.imdecode(encoded,cv2.IMREAD_COLOR))
                self.assertEqual(obs.state,'BOSS')
                self.assertTrue(obs.red or obs.red_uncertain,(name,quality))
                obs=replace(obs,chance=35,base=30,bonus=5)
                c=RuinsController()
                for t in (1.,1.1,1.2,1.4,1.6,1.8,2.):
                    self.assertNotEqual(c.observe(obs,t),'RETREAT',(name,quality,t))

    def test_red_glow_survives_color_shift_and_dimmed_frame(self):
        for name in ('boss30_bonus_stream','boss50_red'):
            image=self.image(name)
            hsv=cv2.cvtColor(image,cv2.COLOR_BGR2HSV)
            patch=hsv[110:170,135:225].copy()
            patch[:,:,0]=((patch[:,:,0].astype(np.int16)+6)%180).astype(np.uint8)
            patch[:,:,2]=(patch[:,:,2].astype(np.float32)*.8).astype(np.uint8)
            hsv[110:170,135:225]=patch
            obs=RuinsDetector().detect(cv2.cvtColor(hsv,cv2.COLOR_HSV2BGR))
            self.assertTrue(obs.red,name)

    def test_single_ambiguous_color_frame_does_not_stall_normal_treasure(self):
        c=RuinsController();uncertain=RuinsObservation('BOSS',35,red_uncertain=True)
        self.assertIsNone(c.observe(uncertain,1.))
        normal=RuinsObservation('BOSS',35)
        for t in (1.1,1.3,1.5,1.7):self.assertIsNone(c.observe(normal,t))
        self.assertEqual(c.observe(normal,1.9),'RETREAT')
        self.assertFalse(c.possible_valuable)

    def test_conflicting_chance_is_not_forgotten_after_read_window(self):
        c=RuinsController();high=RuinsObservation('BOSS',80,red=True)
        self.assertIsNone(c.observe(high,1.))
        low=RuinsObservation('BOSS',0,red=True)
        for i in range(1,25):self.assertIsNone(c.observe(low,1+i*.1))
        self.assertEqual(c.observe(low,3.5),'FIGHT')
        self.assertTrue(c.odds_conflict)
        self.assertTrue(c.fallback_fight)
        c.commit('FIGHT',3.5)
        c.observe(RuinsObservation('UNKNOWN'),7.1)
        c.observe(RuinsObservation('UNKNOWN'),12.1)
        for t in (12.2,12.3,12.4):self.assertIsNone(c.observe(low,t))
        self.assertTrue(c.odds_conflict)
        c.observe(RuinsObservation('ADVANCE'),12.5)
        for t in (12.6,12.7,12.8):self.assertIsNone(c.observe(low,t))
        self.assertTrue(c.odds_conflict)
        c.clear_observation()
        for t in (13.,13.1,13.2):self.assertIsNone(c.observe(low,t))
        error=RuinsObservation('ERROR',target=(.5,.6))
        for t in (13.3,13.4,13.5):c.observe(error,t)
        for t in (13.6,13.7,13.8):self.assertIsNone(c.observe(low,t))
        for t in (13.9,14.,14.1):c.observe(RuinsObservation('REWARD'),t)
        for t in (14.2,14.3):self.assertIsNone(c.observe(low,t))
        self.assertEqual(c.observe(low,14.4),'RETREAT')

    def test_battle_result_ends_old_encounter_without_clearing_red_evidence(self):
        for name in ('battle_win', 'battle_loss'):
            self.assertEqual(RuinsDetector().detect(self.image(name)).state, 'BATTLE_RESULT')
        c = RuinsController()
        high = RuinsObservation('BOSS', 80)
        for t in (1., 1.1, 1.2):
            action = c.observe(high, t)
        self.assertEqual(action, 'FIGHT')
        c.commit(action, 1.2)
        for t in (2., 2.1, 2.2):
            c.observe(RuinsObservation('UNKNOWN'), t)
        self.assertEqual((c.boss_min, c.boss_max), (80, 80))
        result = RuinsObservation('BATTLE_RESULT')
        self.assertIsNone(c.observe(result, 3.))
        self.assertEqual((c.boss_min, c.boss_max), (80, 80))
        self.assertIsNone(c.observe(result, 3.1))
        self.assertIsNone(c.observe(result, 3.2))
        self.assertEqual((c.boss_min, c.boss_max), (None, None))
        low = RuinsObservation('BOSS', 30, base=25, bonus=5)
        actions = [c.observe(low, 10 + i/10) for i in range(13)]
        self.assertIn('RETREAT', actions)
        self.assertFalse(c.odds_conflict)
        c.valuable = c.possible_valuable = True
        for t in (12., 12.1, 12.2):
            c.observe(result, t)
        self.assertTrue(c.valuable)
        self.assertTrue(c.possible_valuable)

    def test_ambiguous_treasure_never_uses_normal_threshold(self):
        c=RuinsController();uncertain=RuinsObservation('BOSS',35,red_uncertain=True)
        for i in range(25):self.assertIsNone(c.observe(uncertain,1+i*.1))
        self.assertEqual(c.observe(uncertain,3.5),'FIGHT')
        self.assertTrue(c.treasure_uncertain)
        self.assertTrue(c.fallback_fight)

    def test_geometry_learns_shift_and_reuses_it_for_other_states(self):
        detector=RuinsDetector()
        def shift(name,dx,dy):
            return cv2.warpAffine(self.image(name),np.float32([[1,0,dx],[0,1,dy]]),(360,800),borderValue=(22,22,22))
        for _ in range(240):obs=detector.detect(shift('advance',24,30))
        self.assertEqual(obs.state,'ADVANCE')
        self.assertTrue(detector.geometry.ready)
        self.assertAlmostEqual(detector.geometry.offset[0],24/360,delta=.006)
        self.assertAlmostEqual(detector.geometry.offset[1],30/800,delta=.006)
        self.assertEqual(detector.detect(shift('milestone',24,30)).state,'MILESTONE')
        self.assertEqual(detector.detect(shift('reward',24,30)).state,'REWARD')
        obs=detector.detect(shift('boss45',24,30))
        self.assertEqual((obs.state,obs.chance),('BOSS',50))
        for _ in range(280):obs=detector.detect(shift('advance',-20,-30))
        self.assertEqual(obs.state,'ADVANCE')
        self.assertAlmostEqual(detector.geometry.offset[0],-20/360,delta=.008)
        self.assertAlmostEqual(detector.geometry.offset[1],-30/800,delta=.008)

    def test_shifted_advance_and_milestone_do_not_become_claim(self):
        for name in ('advance','milestone'):
            detector=RuinsDetector()
            frame=cv2.warpAffine(self.image(name),np.float32([[1,0,0],[0,1,72]]),(360,800))
            for _ in range(30):
                self.assertNotEqual(detector.detect(frame).state,'CLAIM')

    def test_can_calibrate_from_shifted_reward_on_connect(self):
        detector=RuinsDetector()
        frame=cv2.warpAffine(self.image('reward'),np.float32([[1,0,24],[0,1,-30]]),(360,800))
        for _ in range(150):obs=detector.detect(frame)
        self.assertEqual(obs.state,'REWARD')
        self.assertGreater(detector.geometry.offset[0],0)
        self.assertLess(detector.geometry.offset[1],0)

    def test_side_bars_and_tall_aspect_keep_ruins_states(self):
        for left,right in ((20,20),(0,40),(40,0)):
            for name,state,chance in (('advance','ADVANCE',None),('boss45','BOSS',50),
                                      ('reward','REWARD',None),('lobby','LOBBY',None)):
                with self.subTest(left=left,right=right,name=name):
                    image=cv2.copyMakeBorder(self.image(name),0,0,left,right,cv2.BORDER_CONSTANT,value=(0,0,0))
                    d=RuinsDetector()
                    for _ in range(45):obs=d.detect(image)
                    self.assertEqual((obs.state,obs.chance),(state,chance))
                    self.assertAlmostEqual(d.viewport[0],left/(360+left+right),delta=.005)
        for top,bottom in ((40,40),(0,80),(80,0)):
            for name,state,chance in (('advance','ADVANCE',None),('boss45','BOSS',50),('lobby','LOBBY',None)):
                with self.subTest(top=top,bottom=bottom,name=name):
                    image=cv2.copyMakeBorder(self.image(name),top,bottom,0,0,cv2.BORDER_CONSTANT,value=(0,0,0))
                    d=RuinsDetector()
                    for _ in range(195):obs=d.detect(image)
                    self.assertEqual((obs.state,obs.chance),(state,chance))

    def test_dark_screen_does_not_change_side_viewport(self):
        from fisher.ruins_geometry import side_viewport
        self.assertIsNone(side_viewport(np.zeros((800,360,3),np.uint8)))

    def test_manual_detector_never_learns_or_reads_automatic_viewport(self):
        detector=RuinsDetector(offset=(.1,-.1),adaptive=False)
        image=cv2.copyMakeBorder(self.image('advance'),0,0,40,0,cv2.BORDER_CONSTANT,value=(0,0,0))
        with patch('fisher.ruins.side_viewport',side_effect=AssertionError('unexpected auto viewport')):
            with patch.object(detector.geometry,'offer',side_effect=AssertionError('unexpected learning')):
                for _ in range(60):detector.detect(image)
        self.assertEqual(detector.viewport,(0.,1.))
        self.assertEqual(detector.geometry.offset,(0.,0.))

    def test_manual_mode_never_loads_device_profile(self):
        from fisher.ruins_runtime import RuinsRunner
        from adb_app import PHONE_DEFAULTS
        with patch('fisher.phone_runtime.Adb'):
            runner=RuinsRunner('adb','test',dict(PHONE_DEFAULTS,layout_mode='manual'),(2670,1200),'com.game')
        with patch('fisher.ruins_runtime.DeviceProfileStore',side_effect=AssertionError('unexpected profile')):
            detector,profiles,saved=runner._detector_for(runner.settings)
        self.assertFalse(detector.adaptive)
        self.assertIsNone(profiles);self.assertIsNone(saved)

    def test_reconfigure_preserves_counts_and_switches_layout_and_controls(self):
        from fisher.ruins_runtime import RuinsRunner
        from adb_app import PHONE_DEFAULTS
        with patch('fisher.phone_runtime.Adb'):
            runner=RuinsRunner('adb','test',dict(PHONE_DEFAULTS,layout_mode='auto'),(2670,1200),'com.game')
        controller=RuinsController(runner.settings);controller.started=7;controller.completed=6
        controller.commit('ADVANCE',10.)
        old_detector=RuinsDetector(offset=(.03,.02));profiles=Mock()
        manual=dict(runner.settings,layout_mode='manual',ruins_normal_threshold=50,
                    ruins_red_threshold=35,ruins_tap_interval=.6,ruins_tap_max=2,
                    ruins_points={'ADVANCE':[.43,.74]},stream_delay_ms=90)
        with patch('fisher.ruins_runtime.DeviceProfileStore',side_effect=AssertionError('unexpected profile')):
            detector,profiles,saved,rebuilt=runner._apply_reconfigure(controller,old_detector,profiles,manual)
        self.assertTrue(rebuilt);self.assertFalse(detector.adaptive)
        self.assertIsNone(profiles);self.assertIsNone(saved)
        self.assertEqual((controller.started,controller.completed),(7,6))
        self.assertEqual((controller.normal_threshold,controller.red_threshold),(50,35))
        self.assertIsNone(controller.candidate)
        self.assertEqual(controller.last_action,{'ADVANCE':10.})
        self.assertAlmostEqual(runner.capture.delay,.09)
        self.assertEqual(runner.settings['ruins_points']['ADVANCE'],[.43,.74])
        auto=dict(manual,layout_mode='auto')
        with patch('fisher.ruins_runtime.DeviceProfileStore') as store:
            store.return_value.load.return_value=(.03,.02)
            detector,profiles,saved,rebuilt=runner._apply_reconfigure(controller,detector,profiles,auto)
        self.assertTrue(rebuilt);self.assertTrue(detector.adaptive)
        self.assertEqual(saved,(.03,.02))
        self.assertEqual((controller.started,controller.completed),(7,6))

    def test_manual_tap_ignores_automatic_offsets_and_queued_commands(self):
        from fisher.ruins_runtime import RuinsRunner
        from fisher.adb import Frame
        from adb_app import PHONE_DEFAULTS
        cfg=dict(PHONE_DEFAULTS,humanize=False,layout_mode='manual',ruins_points={'ADVANCE':[.43,.74]})
        with patch('fisher.phone_runtime.Adb'):
            runner=RuinsRunner('adb','test',cfg,(2670,1200),'com.game')
        runner.observe_only=False;runner.active.set();runner.foreground_ok=True
        now=time.perf_counter();runner.foreground_at=now
        frame=Frame(np.zeros((800,360,3),dtype=np.uint8),now,now,.02,1)
        runner.commands.put(('reconfigure',dict(cfg)))
        runner._ruins_tap(RuinsController(),'ADVANCE',frame,(0,0,360,800),offset=(.1,.1),viewport=(.1,.8))
        runner.adb.tap.assert_not_called()
        runner.commands.get_nowait()
        runner._ruins_tap(RuinsController(),'ADVANCE',frame,(0,0,360,800),offset=(.1,.1),viewport=(.1,.8))
        x,y=runner.adb.tap.call_args.args
        self.assertAlmostEqual(x,.43*1200,places=3)
        self.assertAlmostEqual(y,.74*2670,places=3)

    def test_error_tap_uses_detected_center_and_human_press_is_bounded(self):
        from fisher.ruins_runtime import RuinsRunner
        from fisher.adb import Frame
        from adb_app import PHONE_DEFAULTS
        with patch('fisher.phone_runtime.Adb'):
            runner=RuinsRunner('adb','test',dict(PHONE_DEFAULTS,humanize=True),(2670,1200),'com.game')
        runner.observe_only=False;runner.active.set();runner.foreground_ok=True
        now=time.perf_counter();runner.foreground_at=now
        frame=Frame(np.zeros((800,360,3),dtype=np.uint8),now,now,.02,1)
        runner._ruins_tap(RuinsController(),'ERROR',frame,(0,0,360,800),
                          offset=(.1,.1),viewport=(.1,.8),target=(.5,.643))
        x,y=runner.adb.tap.call_args.args
        hold=runner.adb.tap.call_args.kwargs['hold_ms']
        self.assertLess(abs(x-.5*1200),.005*1200)
        self.assertLess(abs(y-.643*2670),.003*2670)
        self.assertTrue(45<=hold<=90)

    def test_legacy_burst_settings_do_not_repeat_clicks(self):
        c=RuinsController({'humanize':True,'ruins_tap_interval':.12,'ruins_tap_max':6})
        obs=RuinsObservation('ADVANCE')
        c.observe(obs,1.);c.observe(obs,1.1)
        self.assertEqual(c.observe(obs,1.2),'ADVANCE');c.commit('ADVANCE',1.2)
        for t in (1.4,1.6,2.,3.,5.9):self.assertIsNone(c.observe(obs,t))
        self.assertEqual(c.observe(obs,6.3),'ADVANCE')

    def test_reset_calibration_discards_profile_on_control_thread(self):
        from fisher.ruins_runtime import RuinsRunner
        from adb_app import PHONE_DEFAULTS
        with patch('fisher.phone_runtime.Adb'):
            runner=RuinsRunner('adb','test',dict(PHONE_DEFAULTS,layout_mode='auto'),(2670,1200),'com.game')
        controller=RuinsController(runner.settings);controller.started=4;controller.completed=3
        with patch('fisher.ruins_runtime.DeviceProfileStore') as store:
            store.return_value.load.return_value=(.1,.1)
            detector,profiles,saved,rebuilt=runner._apply_reconfigure(
                controller,RuinsDetector(offset=(.1,.1)),store.return_value,dict(runner.settings),True)
        self.assertTrue(rebuilt);self.assertTrue(detector.adaptive)
        self.assertEqual(detector.geometry.offset,(0.,0.));self.assertIsNone(saved)
        store.return_value.clear.assert_called_once()
        store.return_value.load.assert_not_called()
        self.assertEqual((controller.started,controller.completed),(4,3))

    def test_queued_reconfigure_applies_only_on_new_frame_and_keeps_counts(self):
        from fisher.ruins_runtime import RuinsRunner
        from fisher.adb import Frame
        from adb_app import PHONE_DEFAULTS
        class Capture:
            def __init__(self):
                self.width=360;self.height=800;self.latest=None
                self.delay=.06;self.uncertainty=.012
                self.available=threading.Event();self.thread=Mock()
            def snapshot(self):
                self.available.clear();return self.latest,None
            def publish(self,seq):
                now=time.perf_counter()
                self.latest=Frame(np.full((800,360,3),seq,np.uint8),now,now,.02,seq)
                self.available.set()
            def fps(self,now):return 60.
            def close(self):pass
        class Detector:
            calls=[]
            def __init__(self,offset=None,adaptive=True):
                self.adaptive=adaptive;self.viewport=(0.,1.)
                self.geometry=Mock(offset=(0.,0.),ready=False)
            def detect(self,image):
                self.calls.append((self.adaptive,int(image[0,0,0])))
                return RuinsObservation('ADVANCE')
        def wait_for(predicate):
            end=time.monotonic()+3
            while not predicate() and time.monotonic()<end:time.sleep(.01)
            self.assertTrue(predicate())
        with patch('fisher.phone_runtime.Adb'), patch('fisher.ruins_runtime.DeviceProfileStore'), patch('fisher.ruins_runtime.RuinsDetector',Detector):
            runner=RuinsRunner('adb','test',dict(PHONE_DEFAULTS,layout_mode='auto',humanize=False),(2670,1200),'com.game')
            runner.capture=Capture();runner.foreground_ready=lambda now:True
            runner.active.set();runner.session_started.set();runner.observe_only=False
            runner.capture.publish(1)
            thread=threading.Thread(target=runner._run,daemon=True);thread.start()
            try:
                wait_for(lambda:len(Detector.calls)>=1)
                runner.controller.started=4;runner.controller.completed=3
                runner.controller.commit('ADVANCE',time.perf_counter())
                settings=dict(runner.settings,layout_mode='manual',ruins_normal_threshold=55)
                self.assertTrue(runner.reconfigure(settings))
                wait_for(lambda:runner.settings['layout_mode']=='manual')
                calls_before=len(Detector.calls)
                time.sleep(.12)
                self.assertEqual(len(Detector.calls),calls_before)
                self.assertEqual((runner.controller.started,runner.controller.completed),(4,3))
                self.assertIn('ADVANCE',runner.controller.last_action)
                runner.adb.tap.assert_not_called()
                runner.capture.publish(2)
                wait_for(lambda:len(Detector.calls)>calls_before)
                self.assertEqual(Detector.calls[-1],(False,2))
                self.assertEqual(runner.controller.normal_threshold,55)
                runner.adb.tap.assert_not_called()
            finally:
                runner.stop.set();runner.capture.available.set();thread.join(3)
            self.assertFalse(thread.is_alive())

    def test_geometry_offset_moves_configured_point_within_frame(self):
        from fisher.ruins_runtime import RuinsRunner
        from fisher.adb import Frame
        from adb_app import PHONE_DEFAULTS
        cfg=dict(PHONE_DEFAULTS, humanize=False, ruins_points={'ADVANCE':[.43,.74]})
        with patch('fisher.phone_runtime.Adb'):
            runner=RuinsRunner('adb','test',cfg,(2670,1200),'com.game')
        runner.observe_only=False;runner.active.set();runner.foreground_ok=True
        now=time.perf_counter();runner.foreground_at=now
        frame=Frame(np.zeros((800,360,3),dtype=np.uint8),now,now,.02,1)
        runner._ruins_tap(RuinsController(), 'ADVANCE', frame, (0,0,360,800), offset=(.05,.03))
        x,y=runner.adb.tap.call_args.args
        self.assertAlmostEqual(x,.48*1200,places=3)
        self.assertAlmostEqual(y,.77*2670,places=3)

    def test_side_viewport_maps_default_points_and_preserves_manual_point(self):
        from fisher.ruins_runtime import RuinsRunner
        from fisher.adb import Frame
        from adb_app import PHONE_DEFAULTS
        cfg=dict(PHONE_DEFAULTS,humanize=False,ruins_points={'ADVANCE':[.43,.74]})
        with patch('fisher.phone_runtime.Adb'):
            runner=RuinsRunner('adb','test',cfg,(2670,1200),'com.game')
        runner.observe_only=False;runner.active.set();runner.foreground_ok=True
        now=time.perf_counter();runner.foreground_at=now
        frame=Frame(np.zeros((800,360,3),dtype=np.uint8),now,now,.02,1)
        runner._ruins_tap(RuinsController(),'FIGHT',frame,(0,0,360,800),viewport=(.1,.9))
        x,y=runner.adb.tap.call_args.args
        self.assertAlmostEqual(x,(.1+.9*.73)*1200,places=3)
        runner._ruins_tap(RuinsController(),'ADVANCE',frame,(0,0,360,800),viewport=(.1,.9))
        x,y=runner.adb.tap.call_args.args
        self.assertAlmostEqual(x,.43*1200,places=3)

    def test_unreadable_or_conflicting_odds_fight_after_short_wait(self):
        for chances in ((None,), (30, 80), (44, 45)):
            controller=RuinsController()
            for i in range(25):
                now=1+i*.1;chance=chances[i%len(chances)]
                self.assertIsNone(controller.observe(RuinsObservation('BOSS',chance,red=True),now))
            self.assertEqual(controller.observe(RuinsObservation('BOSS',chances[25%len(chances)],red=True),3.5),'FIGHT')
            self.assertTrue(controller.fallback_fight)
            controller.commit('FIGHT',3.5)
            for now in (3.6,4.,8.,11.4):
                self.assertIsNone(controller.observe(RuinsObservation('BOSS',None,red=True),now))

    def test_unreadable_boss_survives_brief_unrelated_frames_without_double_tapping(self):
        controller=RuinsController()
        for i in range(25):
            state = ('UNKNOWN' if i == 5 else 'ADVANCE' if i == 13 else 'BOSS')
            self.assertIsNone(controller.observe(RuinsObservation(state),1+i*.1))
        self.assertEqual(controller.observe(RuinsObservation('BOSS'),3.5),'FIGHT')
        self.assertTrue(controller.fallback_fight)
        controller.commit('FIGHT',3.5)
        for i in range(1,80):
            self.assertIsNone(controller.observe(RuinsObservation('BOSS'),3.5+i*.1))
        self.assertEqual(controller.observe(RuinsObservation('BOSS'),11.51),'FIGHT')

    def test_fallback_restarts_after_confirmed_screen_change(self):
        controller=RuinsController()
        for now in (1.,1.2,1.4,1.6):
            self.assertIsNone(controller.observe(RuinsObservation('BOSS'),now))
        for now in (1.7,1.8,1.9):
            controller.observe(RuinsObservation('ADVANCE'),now)
        for now in (2.,2.1,2.2,2.4):
            self.assertIsNone(controller.observe(RuinsObservation('BOSS'),now))

    def test_readable_red_eighty_interspersed_with_missing_frames_fights(self):
        controller=RuinsController()
        for now,chance in ((1.,80),(1.1,None),(1.2,80),(1.3,None)):
            self.assertIsNone(controller.observe(RuinsObservation('BOSS',chance,red=True),now))
        self.assertEqual(controller.observe(RuinsObservation('BOSS',80,red=True),1.4),'FIGHT')

    def test_compressed_red_eighty_with_bonus_fights_after_prolonged_unreadable_frames(self):
        image=self.image('boss80_bonus_stream')
        image[110:170,135:225]=self.image('boss50_red')[110:170,135:225]
        ok,encoded=cv2.imencode('.jpg',image,[int(cv2.IMWRITE_JPEG_QUALITY),95])
        self.assertTrue(ok)
        obs=RuinsDetector().detect(cv2.imdecode(encoded,cv2.IMREAD_COLOR))
        self.assertEqual((obs.base,obs.bonus,obs.chance,obs.red),(80,5,85,True))
        c=RuinsController()
        for i in range(10):
            self.assertIsNone(c.observe(RuinsObservation('BOSS',None,red=True),1.+i*.1))
        for t in (2.,2.1):self.assertIsNone(c.observe(obs,t))
        self.assertEqual(c.observe(obs,2.2),'FIGHT')

    def test_boss_consensus_does_not_carry_to_another_screen_or_after_pause(self):
        for interrupt in ('UNKNOWN','ADVANCE','pause'):
            controller=RuinsController()
            for now in (1.,1.1):self.assertIsNone(controller.observe(RuinsObservation('BOSS',80),now))
            if interrupt=='pause':controller.clear_observation()
            else:controller.observe(RuinsObservation(interrupt),1.15)
            self.assertIsNone(controller.observe(RuinsObservation('BOSS',80),1.2))
            self.assertIsNone(controller.observe(RuinsObservation('BOSS',80),1.3))
            self.assertEqual(controller.observe(RuinsObservation('BOSS',80),1.4),'FIGHT')

    def test_boss_timeout_restarts_after_interruption_and_never_taps_unknown(self):
        c=RuinsController()
        for now in (1.,2.,3.):c.observe(RuinsObservation('BOSS'),now)
        c.clear_observation()
        for now in (50.,51.,52.):self.assertIsNone(c.observe(RuinsObservation('BOSS'),now))
        for now in (70.,71.,72.):self.assertIsNone(c.observe(RuinsObservation('UNKNOWN'),now))
        self.assertIsNone(c.observe(RuinsObservation('BOSS'),73.))

    def test_ambiguous_input_waits_for_new_screen(self):
        controller=RuinsController();controller.commit('FIGHT',10,uncertain=True)
        for now in (20,21,22,23):self.assertIsNone(controller.observe(RuinsObservation('BOSS',80),now))
        controller.observe(RuinsObservation('REWARD'),24)
        self.assertIsNone(controller.uncertain_state)

    def test_ambiguous_input_recovers_after_same_screen_is_fresh_for_twelve_seconds(self):
        for action,obs in (('FIGHT',RuinsObservation('BOSS',80)),
                           ('ADVANCE',RuinsObservation('ADVANCE'))):
            c=RuinsController();c.commit(action,10.,uncertain=True)
            for i in range(120):
                self.assertIsNone(c.observe(obs,11.+i*.1))
            self.assertEqual(c.observe(obs,23.1),action)
            self.assertIsNone(c.uncertain_state)

    def test_ambiguous_input_recovery_restarts_on_pause_or_missing_frames(self):
        c=RuinsController();c.commit('FIGHT',10.,uncertain=True)
        obs=RuinsObservation('BOSS',80)
        for i in range(90):self.assertIsNone(c.observe(obs,11.+i*.1))
        c.clear_observation()
        for i in range(60):self.assertIsNone(c.observe(obs,30.+i*.1))
        c.observe(RuinsObservation('UNKNOWN'),36.)
        c.observe(RuinsObservation('UNKNOWN'),37.)
        for i in range(60):self.assertIsNone(c.observe(obs,38.+i*.1))

    def test_runner_checks_foreground_and_frame_age_before_input(self):
        from fisher.ruins_runtime import RuinsRunner
        from fisher.adb import Frame
        from adb_app import PHONE_DEFAULTS
        with patch('fisher.phone_runtime.Adb'):
            runner=RuinsRunner('adb','test',dict(PHONE_DEFAULTS),(2670,1200),'com.game')
        runner.observe_only=False;runner.active.set();runner.foreground_ok=True
        now=time.perf_counter();runner.foreground_at=now
        frame=Frame(np.zeros((800,360,3),dtype=np.uint8),now,now,.02,1)
        ctrl=RuinsController()
        runner.foreground_ok=False;runner._ruins_tap(ctrl,'FIGHT',frame,(0,0,360,800))
        runner.adb.tap.assert_not_called()
        runner.foreground_ok=True;runner._ruins_tap(ctrl,'RETREAT',frame,(0,0,360,800))
        x,y=runner.adb.tap.call_args.args
        self.assertLess(x,600);self.assertGreater(y,1800)
        self.assertIn('RETREAT',ctrl.last_action)
        old=Frame(frame.image,now-10,now-10,.02,2);runner.adb.tap.reset_mock()
        runner._ruins_tap(ctrl,'FIGHT',old,(0,0,360,800));runner.adb.tap.assert_not_called()

    def test_low_chance_is_not_promoted_by_plus_bonus_or_image_compression(self):
        image=self.image('boss45');zero=self.image('boss90')
        image[706:724,261:269]=zero[706:724,261:269]
        for quality in (80,95,100):
            ok,encoded=cv2.imencode('.jpg',image,[int(cv2.IMWRITE_JPEG_QUALITY),quality]);self.assertTrue(ok)
            obs=self.detector.detect(cv2.imdecode(encoded,cv2.IMREAD_COLOR))
            self.assertEqual(obs.state,'BOSS')
            self.assertIn(obs.chance,(None,45))

        # Compression can remove the left edge of a 3 and make it resemble 5.
        red35=self.image('boss30_bonus_stream')
        for quality in (80,90,95,100):
            ok,encoded=cv2.imencode('.jpg',red35,[int(cv2.IMWRITE_JPEG_QUALITY),quality]);self.assertTrue(ok)
            obs=self.detector.detect(cv2.imdecode(encoded,cv2.IMREAD_COLOR))
            self.assertEqual((obs.base,obs.bonus,obs.chance),(30,5,35))

    def test_round_count_only_once_per_screen(self):
        c=RuinsController();c.commit('LOBBY',1);c.commit('LOBBY',7)
        self.assertEqual(c.started,0)
        for t in (8.,8.1,8.2):c.observe(RuinsObservation('ADVANCE'),t)
        self.assertEqual(c.started,1)
        c.commit('CLAIM',9);c.commit('CLAIM',15)
        self.assertEqual(c.completed,0)
        for t in (16.,16.1,16.2):c.observe(RuinsObservation('LOBBY'),t)
        self.assertEqual(c.completed,1)
        c.commit('LOBBY',17)
        for t in (18.,18.1,18.2):c.observe(RuinsObservation('ADVANCE'),t)
        self.assertEqual(c.started,2)


if __name__ == '__main__':
    unittest.main()
