import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import CheckButtons

# --- KONFIGURACE GEOMETRIE ---
TOWER_DIST = 0.18
TOWER_DIA = 0.018
d = TOWER_DIST / 2
TOWER_POS = np.array([[-d, -d], [d, -d], [d, d], [-d, d]])

class AnemometerVisualizer:
    def __init__(self):
        self.v_inf = 10.0
        self.angles = np.linspace(0, 2 * np.pi, 100)
        self.dist_points = np.linspace(-d, d, 40)

        # Nastavení grafu pro profi vzhled
        plt.rcParams['font.family'] = 'serif'
        self.fig = plt.figure("Analýza stínění věží", figsize=(12, 8))
        self.ax = self.fig.add_subplot(111, projection='3d')

        self.surfaces = []
        self.labels = ['Pár V1-V3 (Modře)', 'Pár V2-V4 (Zeleně)', 'Chyba', 'Věže (Černě)']

        self.render()
        self.add_widgets()
        plt.show()

    def get_velocity_at(self, px, py, a_rad):
        u, v = self.v_inf * np.cos(a_rad), self.v_inf * np.sin(a_rad)
        for tx, ty in TOWER_POS:
            dx, dy = px-tx, py-ty
            dist = np.sqrt(dx**2 + dy**2)
            if dist < TOWER_DIA/2: return 0.0, 0.0
            d_par = dx*np.cos(a_rad) + dy*np.sin(a_rad)
            d_perp = -dx*np.sin(a_rad) + dy*np.cos(a_rad)
            if d_par > 0:
                w_w = TOWER_DIA * (1 + 0.4 * np.sqrt(d_par/TOWER_DIA))
                reduction = 0.85 * np.exp(-3.5 * (d_perp/w_w)**2) * (TOWER_DIA/(d_par + TOWER_DIA))
                u -= reduction * self.v_inf * np.cos(a_rad)
                v -= reduction * self.v_inf * np.sin(a_rad)
        return u, v

    def render(self):
        # Výpočet dat
        A, D = np.meshgrid(self.angles, self.dist_points)
        V1, V2 = np.zeros_like(A), np.zeros_like(A)

        p13 = (TOWER_POS[2] - TOWER_POS[0]) / np.linalg.norm(TOWER_POS[2] - TOWER_POS[0])
        p24 = (TOWER_POS[3] - TOWER_POS[1]) / np.linalg.norm(TOWER_POS[3] - TOWER_POS[1])
        c13 = (TOWER_POS[0] + TOWER_POS[2]) / 2
        c24 = (TOWER_POS[1] + TOWER_POS[3]) / 2

        for i in range(len(self.dist_points)):
            for j in range(len(self.angles)):
                pos1 = c13 + self.dist_points[i] * p13
                vel1 = self.get_velocity_at(pos1[0], pos1[1], self.angles[j])
                V1[i, j] = abs(np.dot(vel1, p13))

                pos2 = c24 + self.dist_points[i] * p24
                vel2 = self.get_velocity_at(pos2[0], pos2[1], self.angles[j])
                V2[i, j] = abs(np.dot(vel2, p24))

        V_tot = np.sqrt(V1**2 + V2**2)
        Error = self.v_inf - V_tot

        # Transformace do válcových souřadnic (vizuální efekt prstence)
        R = 20 + D * 40
        X, Y = R * np.cos(A), R * np.sin(A)

        # Vykreslení ploch
        s1 = self.ax.plot_surface(X, Y, V1, cmap='Blues', alpha=0.6, antialiased=True, label=self.labels[0])
        s2 = self.ax.plot_surface(X, Y, V2, cmap='Greens', alpha=0.6, antialiased=True, label=self.labels[1])
        s3 = self.ax.plot_surface(X, Y, -Error, cmap='coolwarm', alpha=0.8, antialiased=True, label=self.labels[2])

        self.surfaces = [s1, s2, s3]

        # Vykreslení věží (jako tenké černé válce)
        tower_plots = []
        for i, (tx, ty) in enumerate(TOWER_POS):
            z_t = np.linspace(-5, 10, 2)
            theta_t = np.linspace(0, 2*np.pi, 20)
            th_g, z_g = np.meshgrid(theta_t, z_t)
            r_vis = 1.2
            xt = tx * 250 + r_vis * np.cos(th_g)
            yt = ty * 250 + r_vis * np.sin(th_g)
            tw = self.ax.plot_surface(xt, yt, z_g, color='black', alpha=0.9)
            tower_plots.append(tw)
        self.surfaces.append(tower_plots)

        # Styling os (podobně jako na obrázku)
        self.ax.set_xlabel('x [mm]', fontsize=10)
        self.ax.set_ylabel('y [mm]', fontsize=10)
        self.ax.set_zlabel('Velocity [m/s]', fontsize=10)
        self.ax.set_title("Systematická chyba měření vlivem konstrukce", fontsize=14, pad=20)

        self.ax.view_init(elev=25, azim=45)
        self.ax.grid(True, linestyle='--', alpha=0.5)

    def add_widgets(self):
        # Přidání boxu s checkboxy pro zapínání/vypínání vrstev
        rax = plt.axes([0.02, 0.4, 0.15, 0.2], frameon=False)
        self.check = CheckButtons(rax, self.labels, [True, True, True, True])

        def func(label):
            idx = self.labels.index(label)
            surf = self.surfaces[idx]

            # Matplotlib handling pro seznam objektů (věže) vs jeden objekt (plocha)
            if isinstance(surf, list):
                for s in surf:
                    s.set_visible(not s.get_visible())
            else:
                surf.set_visible(not surf.get_visible())
            plt.draw()

        self.check.on_clicked(func)

if __name__ == "__main__":
    AnemometerVisualizer()
