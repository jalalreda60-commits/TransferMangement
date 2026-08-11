"""
ui/widgets/charts.py
-----------------------
Small matplotlib canvases (FigureCanvasQTAgg) used across the Dashboard:
  * DonutChart          - status / type distributions
  * BarChart            - categorical counts (Technology, Sender/Receiver location)
  * HorizontalBarChart  - per-transfer progress bars
  * LineChart           - weekly progress trend
All are theme-aware (light/dark) and degrade gracefully to an empty-state
message when there's no data yet.
"""
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas


class _BaseChart(FigureCanvas):
    def __init__(self, figsize=(4, 3), dark_mode: bool = False, parent=None):
        self.dark_mode = dark_mode
        self.fig = Figure(figsize=figsize, dpi=100)
        super().__init__(self.fig)
        self.setParent(parent)
        self._style_figure()

    def _style_figure(self):
        bg = "#262A32" if self.dark_mode else "#FFFFFF"
        self.fig.patch.set_facecolor(bg)

    def _text_color(self):
        return "#E6E6E6" if self.dark_mode else "#1B1B1F"

    def _grid_color(self):
        return "#3A3F4A" if self.dark_mode else "#DCE2EA"

    def _empty(self, ax, message="No data yet"):
        ax.text(0.5, 0.5, message, ha="center", va="center", color=self._text_color())
        ax.axis("off")


class DonutChart(_BaseChart):
    def plot(self, distribution: dict, color_fn=None):
        self.fig.clear()
        self._style_figure()
        ax = self.fig.add_subplot(111)
        labels = [k for k, v in distribution.items() if v > 0]
        values = [v for v in distribution.values() if v > 0]
        if not values:
            self._empty(ax)
        else:
            colors = [color_fn(l) if color_fn else None for l in labels]
            wedges, _ = ax.pie(
                values, colors=colors if all(colors) else None, startangle=90,
                wedgeprops=dict(width=0.42, edgecolor=("#262A32" if self.dark_mode else "white"), linewidth=2),
            )
            total = sum(values)
            ax.text(0, 0, str(total), ha="center", va="center", fontsize=18, fontweight="bold", color=self._text_color())
            ax.legend(wedges, [f"{l} ({v})" for l, v in zip(labels, values)],
                      loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False,
                      labelcolor=self._text_color(), fontsize=8)
        ax.set_aspect("equal")
        self.fig.tight_layout()
        self.draw()


class BarChart(_BaseChart):
    def plot(self, labels: list[str], values: list[float], color: str = "#0F5FA8"):
        self.fig.clear()
        self._style_figure()
        ax = self.fig.add_subplot(111)
        if not labels:
            self._empty(ax)
        else:
            bars = ax.bar(labels, values, color=color, width=0.55, zorder=3)
            for b, v in zip(bars, values):
                ax.text(b.get_x() + b.get_width() / 2, v + max(values) * 0.02, str(v),
                        ha="center", fontsize=8, color=self._text_color())
            ax.spines[["top", "right", "left"]].set_visible(False)
            ax.spines["bottom"].set_color(self._grid_color())
            ax.tick_params(colors=self._text_color(), labelsize=8, rotation=20)
            ax.yaxis.grid(True, color=self._grid_color(), linewidth=0.6, zorder=0)
            ax.set_axisbelow(True)
        self.fig.tight_layout()
        self.draw()


class HorizontalBarChart(_BaseChart):
    def plot(self, labels: list[str], values: list[float], colors: list[str] | None = None):
        self.fig.clear()
        self._style_figure()
        ax = self.fig.add_subplot(111)
        if not labels:
            self._empty(ax)
        else:
            y_pos = range(len(labels))
            bar_colors = colors or ["#0F5FA8"] * len(labels)
            ax.barh(list(y_pos), values, color=bar_colors, height=0.55, zorder=3)
            ax.set_yticks(list(y_pos))
            ax.set_yticklabels(labels, fontsize=8, color=self._text_color())
            ax.invert_yaxis()
            ax.set_xlim(0, 100)
            for i, v in enumerate(values):
                ax.text(v + 2, i, f"{v:.0f}%", va="center", fontsize=8, color=self._text_color())
            ax.spines[["top", "right", "left"]].set_visible(False)
            ax.spines["bottom"].set_color(self._grid_color())
            ax.tick_params(colors=self._text_color(), labelsize=8)
            ax.xaxis.grid(True, color=self._grid_color(), linewidth=0.6, zorder=0)
            ax.set_axisbelow(True)
        self.fig.tight_layout()
        self.draw()


class LineChart(_BaseChart):
    def plot(self, labels: list[str], values: list[float], color: str = "#0F5FA8"):
        self.fig.clear()
        self._style_figure()
        ax = self.fig.add_subplot(111)
        if not labels:
            self._empty(ax)
        else:
            ax.plot(labels, values, color=color, marker="o", linewidth=2, zorder=3)
            ax.fill_between(range(len(labels)), values, color=color, alpha=0.12, zorder=2)
            ax.spines[["top", "right"]].set_visible(False)
            ax.spines[["bottom", "left"]].set_color(self._grid_color())
            ax.tick_params(colors=self._text_color(), labelsize=8, rotation=20)
            ax.yaxis.grid(True, color=self._grid_color(), linewidth=0.6, zorder=0)
            ax.set_axisbelow(True)
            ax.set_ylim(0, 100)
        self.fig.tight_layout()
        self.draw()
