# SPDX-License-Identifier: GPL-3.0-only
"""Bounded screen-offset learning from recognizable ruins controls."""
import cv2
import numpy as np


def error_dialog_target(image):
    """Return a confirmed error dialog's green-button center, crop-normalized.

    The text's spelling and error code are deliberately not examined. Require
    a purple header, pale panel, narrow red message, one green button that
    overlaps the panel's bottom edge, and a dim background.
    """
    if image is None or image.ndim != 3 or image.shape[2] != 3:return None
    scaled = image if image.shape[:2] == (800,360) else cv2.resize(image,(360,800),interpolation=cv2.INTER_AREA)
    hsv=cv2.cvtColor(scaled,cv2.COLOR_BGR2HSV)
    purple=cv2.inRange(hsv,(112,65,55),(165,255,240))
    if np.count_nonzero(purple[100:600]) < 2500:return None
    green=cv2.inRange(hsv,(35,100,110),(85,255,255))
    if np.count_nonzero(green[200:700]) < 1000:return None
    light=cv2.inRange(hsv,(0,0,180),(180,70,255))
    red=cv2.bitwise_or(cv2.inRange(hsv,(0,90,90),(12,255,255)),
                       cv2.inRange(hsv,(170,90,90),(179,255,255)))
    def components(mask,area):
        _,_,stats,_=cv2.connectedComponentsWithStats(mask)
        return [tuple(map(int,row)) for row in stats[1:] if row[4]>=area]
    headers=components(purple,2500)
    panels=components(light,8000)
    buttons=components(green,700)
    for hx,hy,hw,hh,ha in headers:
        if not (220 <= hw <= 360 and 20 <= hh <= 100 and hw/hh >= 4
                and 70 <= hy <= 500 and ha >= hw*hh*.55):continue
        for px,py,pw,ph,pa in panels:
            if not (abs(px-hx)<=15 and abs((py)-(hy+hh))<=8 and .85*hw <= pw <= 1.08*hw
                    and 75<=ph<=280 and pa>=pw*ph*.50):continue
            top=max(0,hy-100)
            if top==hy or np.mean(hsv[top:hy,:,2] < 120) < .55:continue
            section=red[py:py+ph,px:px+pw]
            points=cv2.findNonZero(section)
            if points is None:continue
            rx,ry,rw,rh=cv2.boundingRect(points); red_area=cv2.countNonZero(section)
            if not (rw >= .18*pw and 5 <= rh <= .24*ph and rw/rh >= 3
                    and .2*ph <= ry+rh/2 <= .8*ph and .004*pw*ph <= red_area <= .17*pw*ph):continue
            matching=[]
            for bx,by,bw,bh,ba in buttons:
                if (65<=bw<=220 and 15<=bh<=75 and bw/bh >= 2
                        and abs((bx+bw/2)-(px+pw/2)) <= .14*pw
                        and py+ph-.22*ph <= by <= py+ph+.08*ph
                        and by+bh > py+ph and ba >= bw*bh*.45):
                    matching.append((bx,by,bw,bh))
            # Two similarly placed green buttons could be a purchase or other
            # choice dialog; do not guess which one to press.
            nearby=[b for b in buttons if b[1] >= py+ph-.22*ph and b[1] < py+ph+.15*ph
                    and b[2]>=45 and b[3]>=15]
            if len(matching)==1 and len(nearby)==1:
                bx,by,bw,bh=matching[0]
                return ((bx+bw/2)/360.,(by+bh/2)/800.)
    return None


def side_viewport(image):
    """Find uniform black side bars, retaining all vertical game content.

    Return None for an inconclusive or mostly dark image. Bars must be almost
    perfectly black for the entire screen height and less than 20% per side.
    """
    h,w=image.shape[:2]
    if h < 100 or w < 100:return None
    rows=image[::max(1,h//160)]
    value=np.max(rows,axis=2)
    dark=np.mean(value < 8,axis=0)
    left=0
    while left<w and dark[left] >= .995:left+=1
    right=0
    while right<w-left and dark[w-1-right] >= .995:right+=1
    if left > .20*w or right > .20*w or w-left-right < .60*w:return None
    if left < max(3,round(.008*w)):left=0
    if right < max(3,round(.008*w)):right=0
    inner=value[:,left:w-right if right else w]
    if not inner.size or np.mean(inner > 24) < .08:return None
    return left/w, (w-left-right)/w


class RuinsGeometry:
    """Track one crop-relative translation only after repeated agreement."""
    LIMIT = .20

    def __init__(self, offset=None):
        self.offset = self.bounded(offset) or (0., 0.)
        self.pending = None
        self.agreements = 0
        self.ready = False

    @classmethod
    def bounded(cls, value):
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            return None
        try:
            point = float(value[0]), float(value[1])
        except (ValueError, TypeError):
            return None
        if not all(np.isfinite(v) and abs(v) <= cls.LIMIT for v in point):
            return None
        return point

    def offer(self, proposal):
        proposal = self.bounded(proposal)
        if proposal is None:
            return False
        if self.pending is None or max(abs(a-b) for a,b in zip(proposal, self.pending)) > .018:
            self.pending, self.agreements = proposal, 1
            self.ready = False
        else:
            self.pending = tuple(.7*a+.3*b for a,b in zip(self.pending, proposal))
            self.agreements += 1
        if self.agreements < 3:
            return False
        self.offset = tuple(.6*a+.4*b for a,b in zip(self.offset, self.pending))
        self.ready = self.agreements >= 12
        return True

    @staticmethod
    def _components(hsv, low, high, close=7):
        mask = cv2.inRange(hsv, low, high)
        mask[:440] = 0
        mask[799:] = 0
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (close, close))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        _, _, stats, _ = cv2.connectedComponentsWithStats(mask)
        return [tuple(map(int, row)) for row in stats[1:] if row[4] >= 250]

    @staticmethod
    def _normal(dx, dy):
        return dx / 360., dy / 800.

    def locate(self, scaled, state):
        """Return an offset candidate; caller must independently confirm state."""
        hsv = cv2.cvtColor(scaled, cv2.COLOR_BGR2HSV)
        if state == 'ADVANCE':
            choices = []
            for x,y,w,h,area in self._components(hsv, (68,100,120), (100,255,255)):
                cx, cy = x+w/2, y+h/2
                if (50 <= w <= 145 and 40 <= h <= 135 and .65 <= w/h <= 1.55
                        and 90 <= cx <= 270 and 500 <= cy <= 750
                        and area >= w*h*.34):
                    choices.append((area, self._normal(cx-180, cy-681)))
            return max(choices, default=(0,None), key=lambda item:item[0])[1]
        if state == 'CLAIM':
            choices = []
            for x,y,w,h,area in self._components(hsv, (35,100,120), (90,255,255)):
                cx,cy=x+w/2,y+h/2
                if (75 <= w <= 240 and 16 <= h <= 80 and w/h >= 2
                        and 90 <= cx <= 270 and 610 <= cy <= 780
                        and y+h < 799 and area >= w*h*.35):
                    choices.append((area, self._normal(cx-180,cy-750)))
            return max(choices, default=(0,None), key=lambda item:item[0])[1]
        if state == 'BOSS':
            left = self._components(hsv, (35,70,45), (85,255,200), 9)
            right = self._components(hsv, (90,70,35), (130,255,200), 9)
            pairs=[]
            for lx,ly,lw,lh,la in left:
                for rx,ry,rw,rh,ra in right:
                    lc,rc=lx+lw/2,rx+rw/2
                    if (75 <= lw <= 190 and 75 <= rw <= 190
                            and 90 <= lh <= 220 and 90 <= rh <= 220
                            and 25 <= lc <= 165 and 195 <= rc <= 335
                            and 110 <= rc-lc <= 210
                            and abs((ly+lh)-(ry+rh)) <= 12
                            and abs(lw-rw) <= 35 and abs(lh-rh) <= 35):
                        pairs.append((la+ra,self._normal((lc+rc)/2-178,((ly+lh)+(ry+rh))/2-741)))
            return max(pairs, default=(0,None), key=lambda item:item[0])[1]
        if state == 'REWARD':
            # The small grayscale footer remains visible across localized loot
            # popups; use it only as a proposal for the dark-modal classifier.
            mask=cv2.inRange(hsv,(0,0,75),(180,80,200))
            mask[:600]=0;mask[790:]=0;mask[:,:50]=0;mask[:,310:]=0
            rows=np.count_nonzero(mask,axis=1)>=8
            starts=[];start=None
            for y,present in enumerate([*rows,False]):
                if present and start is None:start=y
                elif not present and start is not None:
                    if 6 <= y-start <= 28:starts.append((start,y))
                    start=None
            choices=[]
            for top,bottom in starts:
                points=cv2.findNonZero(mask[max(0,top-1):min(800,bottom+1)])
                if points is None:continue
                x,y,w,h=cv2.boundingRect(points);y+=max(0,top-1)
                cx,cy=x+w/2,y+h/2
                if 70 <= w <= 190 and 7 <= h <= 30 and 85 <= cx <= 275:
                    choices.append((w*h,self._normal(cx-180,cy-752)))
            return max(choices, default=(0,None), key=lambda item:item[0])[1]
        if state == 'LOBBY':
            # Locate the orange expedition control by its blue helmet, torch,
            # gold or purple badge and dark rim. None of these regions reads UI text.
            choices=[]
            blue=cv2.inRange(hsv[500:780,40:260],(85,80,55),(130,255,255))
            blue=cv2.morphologyEx(blue,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_RECT,(3,3)))
            _,_,stats,_=cv2.connectedComponentsWithStats(blue)
            for x,y,w,h,area in (tuple(map(int,row)) for row in stats[1:]):
                x+=40;y+=500
                cx,cy=x+w/2,y+h/2
                if (26 <= w <= 72 and 22 <= h <= 65 and .6 <= w/h <= 2
                        and 65 <= cx <= 215 and 560 <= cy <= 750 and area >= w*h*.35):
                    sx,sy=w/43,h/37
                    def fraction(box,lo,hi):
                        x1,y1,x2,y2=map(int,box)
                        x1=max(0,x1);y1=max(0,y1);x2=min(360,x2);y2=min(800,y2)
                        if x1>=x2 or y1>=y2:return 0.
                        return float(np.mean(cv2.inRange(hsv[y1:y2,x1:x2],lo,hi)>0))
                    badge_box=(x+120*sx,y-29*sy,x+172*sx,y+6*sy)
                    badge_gold=fraction(badge_box,(12,90,150),(40,255,255))
                    badge_purple=fraction(badge_box,(112,65,45),(170,255,255))
                    body=fraction((x+47*sx,y+13*sy,x+142*sx,y+60*sy),(5,110,150),(35,255,255))
                    rim=fraction((x-30*sx,y+4*sy,x+157*sx,y+74*sy),(0,0,0),(180,255,60))
                    if (badge_gold>=.08 or badge_purple>=.12) and body>=.25 and rim>=.08:
                        choices.append((area,self._normal(cx-139.5,cy-687.5)))
            return max(choices,default=(0,None),key=lambda item:item[0])[1]
        return None


def shifted_to_reference(scaled, offset):
    """Translate a crop without scaling; negative border pixels stay black."""
    dx,dy=round(offset[0]*360),round(offset[1]*800)
    if not dx and not dy:
        return scaled
    return cv2.warpAffine(scaled, np.float32([[1,0,-dx],[0,1,-dy]]), (360,800),
                          flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT)
