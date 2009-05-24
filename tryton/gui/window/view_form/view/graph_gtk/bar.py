#This file is part of Tryton.  The COPYRIGHT file at the top level of this repository contains the full copyright notices and license terms.
#This code is inspired by the pycha project (http://www.lorenzogil.com/projects/pycha/)
from graph import Graph
from tryton.common import hex2rgb, lighten, float_time_to_text
import locale
import math
import cairo
import tryton.rpc as rpc


class Bar(Graph):

    def drawGraph(self, cr, width, height):

        def drawBar(bar):
            cr.set_line_width(1.0)

            x = self.area.w * bar.x + self.area.x
            y = self.area.h * bar.y + self.area.y
            w = self.area.w * bar.w
            h = self.area.h * bar.h

            if w < 1 or h <1:
                return # don't draw too small

            cr.set_source_rgba(0, 0, 0, 0.15)
            rectangle = self._getShadowRectangle(x, y, w, h)
            self.drawRectangle(cr, *rectangle)
            cr.fill()

            self.drawRectangle(cr, x, y, w, h)
            r, g, b = self.colorScheme[bar.yname]
            if bar.highlight:
                r, g, b = self.colorScheme['__highlight']
            cr.set_source(self.sourceRectangle(x, y, w, h, r, g, b))
            cr.fill_preserve()
            cr.stroke()

        cr.save()
        for bar in self.bars:
            drawBar(bar)
        cr.restore()

    def drawRectangle(self, cr, x, y, w, h):
        cr.arc(x + 5, y + 5, 5, 0, 2 * math.pi)
        cr.arc(x + w - 5, y + 5, 5, 0, 2 * math.pi)
        cr.arc(x + w - 5, y + h - 5, 5, 0, 2 * math.pi)
        cr.arc(x + 5, y + h - 5, 5, 0, 2 * math.pi)
        cr.rectangle(x + 5, y, w - 10, h)
        cr.rectangle(x, y + 5, w, h - 10)

    def sourceRectangle(self, x, y, w, h, r, g, b):
        linear = cairo.LinearGradient((x + w) / 2, y, (x + w) / 2, y + h)
        linear.add_color_stop_rgb(0, 3.5 * r / 5.0, 3.5 * g / 5.0, 3.5 * b / 5.0)
        linear.add_color_stop_rgb(1, r, g, b)
        return linear

    def motion(self, widget, event):
        super(Bar, self).motion(widget, event)

        def intersect(bar, event):
            x = self.area.w * bar.x + self.area.x
            y = self.area.h * bar.y + self.area.y
            w = self.area.w * bar.w
            h = self.area.h * bar.h

            if x <= event.x <= x + w and y <= event.y <= y + h:
                return True
            return False

        highlight = False
        draw_bars = []
        yfields_float_time = dict([(x.get('key', x['name']), x.get('float_time'))
                for x in self.yfields if x.get('widget')])
        for bar in self.bars:
            if intersect(bar, event):
                if not bar.highlight:
                    bar.highlight = True
                    if bar.yname in yfields_float_time:
                        conv = None
                        if yfields_float_time[bar.yname]:
                            conv = rpc.CONTEXT.get(
                                    yfields_float_time[bar.yname])
                        label = float_time_to_text(bar.yval, conv)
                    else:
                        label = locale.format('%.2f', bar.yval, True)
                    label += '\n'
                    label += str(self.labels[bar.xname])
                    self.popup.set_text(label)
                    draw_bars.append(bar)
            else:
                if bar.highlight:
                    bar.highlight = False
                    draw_bars.append(bar)
            if bar.highlight:
                highlight = True

        if highlight:
            self.popup.show()
        else:
            self.popup.hide()

        if draw_bars:
            minx = self.area.w + self.area.x
            miny = self.area.h + self.area.y
            maxx = maxy = 0.0
            for bar in draw_bars:
                x = self.area.w * bar.x + self.area.x
                y = self.area.h * bar.y + self.area.y
                minx = int(min(x, minx))
                miny = int(min(y, miny))
                maxx = int(max(x + self.area.w * bar.w, maxx))
                maxy = int(max(y + self.area.h * bar.h, maxy))
            self.queue_draw_area(minx - 1, miny - 1,
                    maxx - minx + 2, maxy - miny + 2)

    def action(self, window):
        super(Bar, self).action(window)
        for bar in self.bars:
            if bar.highlight:
                ids = self.ids[bar.xname]
                self.action_keyword(ids, window)


class VerticalBar(Bar):
    'Vertical Bar Graph'

    def updateGraph(self):

        barWidth = self.xscale * 0.9
        barMargin = self.xscale * (1.0 - 0.9) / 2

        self.bars = []
        i = 0
        keys = self.datas.keys()
        keys.sort()
        for xfield in keys:
            j = 0
            barWidthForSet = barWidth / len(self.datas[xfield])
            for yfield in self._getDatasKeys():
                xval = i
                yval = self.datas[xfield][yfield]

                x = (xval - self.minxval) * self.xscale + \
                        barMargin + (j * barWidthForSet)
                y = 1.0 - (yval - self.minyval) * self.yscale
                w = barWidthForSet
                h = yval * self.yscale

                if h < 0:
                    h = abs(h)
                    y -= h

                rect = Rect(x, y, w, h, xval, yval, xfield, yfield)
                if (0.0 <= rect.x <= 1.0) and (0.0 <= rect.y <= 1.0):
                    self.bars.append(rect)

                j += 1
            i += 1

    def XLabels(self):
        xlabels = super(VerticalBar, self).XLabels()
        return [(x[0] + (self.xscale / 2), x[1]) for x in xlabels]

    def YLabels(self):
        ylabels = super(VerticalBar, self).YLabels()
        if len([x.get('key', x['name']) for x in self.yfields
            if x.get('widget')]) == len(self.yfields):

            def format(val):
                val = locale.atof(val)
                res = '%02d:%02d' % (math.floor(abs(val)),
                        round(abs(val) % 1 + 0.01, 2) * 60)
                if val < 0:
                    res = '-' + res
                return res
            return [(x[0], format(x[1])) for x in ylabels]
        return ylabels

    def _getShadowRectangle(self, x, y, w, h):
        return (x-2, y-2, w+4, h+2)


class HorizontalBar(Bar):
    'Horizontal Bar Graph'

    def updateGraph(self):

        barWidth = self.xscale * 0.9
        barMargin = self.xscale * (1.0 - 0.9) / 2

        self.bars = []
        i = 0
        keys = self.datas.keys()
        keys.sort()
        for xfield in keys:
            j = 0
            barWidthForSet = barWidth / len(self.datas[xfield])
            for yfield in self._getDatasKeys():
                xval = i
                yval = self.datas[xfield][yfield]

                x = - self.minyval * self.yscale
                y = (xval - self.minxval) * self.xscale + \
                        barMargin + (j * barWidthForSet)
                w = yval * self.yscale
                h = barWidthForSet

                if w < 0:
                    w = abs(w)
                    x -= w

                rect = Rect(x, y, w, h, xval, yval, xfield, yfield)
                if (0.0 <= rect.x <= 1.0) and (0.0 <= rect.y <= 1.0):
                    self.bars.append(rect)

                j += 1
            i += 1

    def YLabels(self):
        xlabels = super(HorizontalBar, self).XLabels()
        return [(1 - (x[0] + (self.xscale / 2)), x[1]) for x in xlabels]

    def XLabels(self):
        ylabels = super(HorizontalBar, self).YLabels()
        if len([x.get('key', x['name']) for x in self.yfields
            if x.get('widget')]) == len(self.yfields):
            conv = None
            float_time = reduce(lambda x, y: x == y and x or False,
                    [x.get('float_time') for x in self.yfields])
            if float_time:
                conv = rpc.CONTEXT.get(float_time)
            return [(x[0], float_time_to_text(locale.atof(x[1]), conv))
                    for x in ylabels]
        return [(x[0], x[1]) for x in ylabels]

    def _getShadowRectangle(self, x, y, w, h):
        return (x, y-2, w+2, h+4)

    def _getLegendPosition(self, width, height):
        return self.area.x + self.area.w * 0.95 - width, \
                self.area.y + self.area.h * 0.05

    def drawLines(self, cr, width, height):
        for w, label in self.XLabels():
            self.drawLine(cr, w, 0)


class Rect(object):

    def __init__(self, x, y, w, h, xval, yval, xname, yname):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.xval, self.yval = xval, yval
        self.yname = yname
        self.xname = xname
        self.highlight = False
