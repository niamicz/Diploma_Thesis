import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from matplotlib.patches import Circle, FancyArrowPatch

# --- GLOBÁLNÍ NASTAVENÍ STYLU PRO DP ---
plt.rcParams.update({
    "font.family": "serif",
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.facecolor": "white",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "--"
})

# --- KONFIGURACE GEOMETRIE (v metrech pro výpočet) ---
TOWER_DIST = 0.18
TOWER_DIA = 0.01
d = TOWER_DIST / 2
TOWER_POS = np.array([[-d, -d], [d, -d], [d, d], [-d, d]])

class AnemometerFinalMaster:
    def __init__(self):
        plt.ion()
        self.fig_ctrl = plt.figure("Anemometr - Analýza proudění", figsize=(14, 8))
        # Rozvržení: [Mapa (vlevo) | Colorbar (střed) | Grafy (vpravo)]
        self.gs = self.fig_ctrl.add_gridspec(2, 3, width_ratios=[1.2, 0.05, 0.8], wspace=0.35, hspace=0.4)

        self.ax_map_theo = self.fig_ctrl.add_subplot(self.gs[:, 0])
        self.ax_cbar = self.fig_ctrl.add_subplot(self.gs[:, 1])
        self.ax_p1 = self.fig_ctrl.add_subplot(self.gs[0, 2])
        self.ax_p2 = self.fig_ctrl.add_subplot(self.gs[1, 2])

        plt.subplots_adjust(bottom=0.22, left=0.08, right=0.95, top=0.92)

        # Ovládací prvky (modernější barvy)
        ax_s_speed = plt.axes([0.15, 0.10, 0.25, 0.025], facecolor='#f0f0f0')
        ax_s_angle = plt.axes([0.15, 0.05, 0.25, 0.025], facecolor='#f0f0f0')
        self.s_speed = Slider(ax_s_speed, 'Rychlost $[m/s]$ ', 1, 30, valinit=15, valfmt='%1.0f')
        self.s_angle = Slider(ax_s_angle, 'Úhel $[^\circ]$ ', 0, 360, valinit=45, valfmt='%1.0f')

        self.btn_calc = Button(plt.axes([0.50, 0.06, 0.12, 0.05]), 'AKTUALIZOVAT', color='#e1f5fe', hovercolor='#b3e5fc')
        self.btn_cfd = Button(plt.axes([0.64, 0.06, 0.12, 0.05]), 'SPUSTIT CFD', color='#fff9c4', hovercolor='#fff176')

        # Směrová šipka (Kompas) - umístěna v rohu mapy
        self.arrow = FancyArrowPatch((-120, 120), (-100, 120), mutation_scale=15, color='#1565c0', arrowstyle='-|>', zorder=25)
        self.ax_map_theo.add_patch(self.arrow)

        self.btn_calc.on_clicked(self.update_theory)
        self.btn_cfd.on_clicked(self.run_stable_vortex_cfd)
        self.s_angle.on_changed(self.quick_arrow_update)

        self.update_theory(None)
        plt.show(block=True)

    def setup_map_axes(self):
        # Převod na milimetry pro osu
        self.ax_map_theo.set_xlim(-150, 150)
        self.ax_map_theo.set_ylim(-150, 150)
        self.ax_map_theo.set_aspect('equal')
        self.ax_map_theo.set_xlabel('$x$ [mm]')
        self.ax_map_theo.set_ylabel('$y$ [mm]')
        self.ax_map_theo.set_title("Vektorové pole rychlosti (Analytický model)", pad=15, weight='bold')

        for i, (tx, ty) in enumerate(TOWER_POS):
            # Převod metrů na mm pro vykreslení
            tx_mm, ty_mm = tx*1000, ty*1000
            self.ax_map_theo.add_patch(Circle((tx_mm, ty_mm), (TOWER_DIA/2)*1000, color='#212121', zorder=10))
            self.ax_map_theo.text(tx_mm, ty_mm+12, f"V{i+1}", ha='center', weight='bold', fontsize=9)

    def quick_arrow_update(self, val):
        angle = np.radians(self.s_angle.val)
        # Šipka indikující směr větru v mm souřadnicích
        r = 30
        self.arrow.set_positions((-120, 120), (-120 + np.cos(angle)*r, 120 + np.sin(angle)*r))
        self.fig_ctrl.canvas.draw_idle()

    def get_velocity_at(self, px, py, v_inf, a_rad):
        # px, py jsou v METRECH
        u, v = v_inf * np.cos(a_rad), v_inf * np.sin(a_rad)
        for tx, ty in TOWER_POS:
            dx, dy = px-tx, py-ty
            dist = np.sqrt(dx**2+dy**2)
            if dist < TOWER_DIA/2: return 0.0, 0.0
            d_par = dx*np.cos(a_rad) + dy*np.sin(a_rad)
            d_perp = -dx*np.sin(a_rad) + dy*np.cos(a_rad)
            if d_par > 0:
                w_w = TOWER_DIA * (1.0 + 0.4 * d_par / TOWER_DIA)
                deficit = 0.8 * v_inf * np.exp(-0.5 * (d_perp / (w_w / 2.5))**2) * (TOWER_DIA / (d_par + TOWER_DIA))
                u -= deficit * np.cos(a_rad)
                v -= deficit * np.sin(a_rad)
        return u, v

    def update_theory(self, event):
        v_ref = self.s_speed.val
        a_rad = np.radians(self.s_angle.val)

        self.ax_map_theo.clear()
        self.setup_map_axes()
        self.ax_map_theo.add_patch(self.arrow)

        # Výpočetní mřížka v metrech
        res = 70
        x_m = np.linspace(-0.15, 0.15, res)
        X_m, Y_m = np.meshgrid(x_m, x_m)
        U, V = np.vectorize(self.get_velocity_at)(X_m, Y_m, v_ref, a_rad)
        speed = np.sqrt(U**2 + V**2)

        # Vykreslení v mm
        X_mm, Y_mm = X_m*1000, Y_m*1000
        strm = self.ax_map_theo.streamplot(X_mm, Y_mm, U, V, color=speed, cmap='viridis',
                                          linewidth=1.2, density=1.4, arrowsize=1.0)

        self.ax_cbar.clear()
        cbar = plt.colorbar(strm.lines, cax=self.ax_cbar)
        cbar.set_label('Rychlost $v$ [m/s]', weight='bold')

        self.draw_profile(self.ax_p1, TOWER_POS[0], TOWER_POS[2], v_ref, a_rad, "Trasa V1 $\\rightarrow$ V3", "#d32f2f")
        self.draw_profile(self.ax_p2, TOWER_POS[1], TOWER_POS[3], v_ref, a_rad, "Trasa V2 $\\rightarrow$ V4", "#388e3c")
        self.fig_ctrl.canvas.draw_idle()

    def draw_profile(self, ax, p1, p2, v_inf, a_rad, title, color):
        ax.clear()
        steps = 100
        path_x = np.linspace(p1[0], p2[0], steps)
        path_y = np.linspace(p1[1], p2[1], steps)
        p_unit = (p2 - p1) / np.linalg.norm(p2 - p1)

        v_ideal = v_inf * (np.cos(a_rad)*p_unit[0] + np.sin(a_rad)*p_unit[1])
        v_act = [np.dot(self.get_velocity_at(px, py, v_inf, a_rad), p_unit) for px, py in zip(path_x, path_y)]

        avg_act = np.mean(v_act)
        err = abs(avg_act - v_ideal) / abs(v_ideal) * 100 if abs(v_ideal) > 0.1 else 0

        ax.plot(np.linspace(0, 100, steps), v_act, color=color, lw=2, label='Model')
        ax.axhline(y=v_ideal, color='#455a64', ls='--', lw=1.2, label='Teorie')
        ax.set_title(f"{title} (Chyba: {err:.1f} %)", fontsize=10, loc='left')
        ax.set_xlabel('Vzdálenost na senzoru [%]')
        ax.set_ylabel('$v_{proj}$ [m/s]')
        ax.set_ylim(-v_inf*0.1, v_inf*1.1)
        if ax == self.ax_p1: ax.legend(loc='lower right', frameon=True)

    def run_stable_vortex_cfd(self, event):
        # CFD kód zůstává stejný, jen přidáme lepší formátování výsledného okna
        print("Spouštím LBM simulaci...")
        # ... (zde by byl tvůj výpočet CFD) ...
        # (na konci CFD okna přidej:)
        # plt.rcParams['font.family'] = 'serif'
        # plt.tight_layout()
        pass

if __name__ == "__main__":
    AnemometerFinalMaster()
