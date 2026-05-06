#include <iostream>
#include <vector>
#include <cmath>
#include <fstream>
#include <algorithm>
#include <string>

// --- KONFIGURACE SIMULACE ---
const int NX = 2000;          // Šířka domény
const int NY = 1000;          // Výška domény
const int STEPS = 12000;     // Počet kroků (dostatek pro vývin vírů)
const double TAU = 0.54;     // Relaxační čas (ovlivňuje viskozitu)
const double U_IN = 0.1;     // Vstupní rychlost proudění

// --- MATICE SMĚRŮ D2Q9 ---
const double w[9] = {4.0/9.0, 1.0/9.0, 1.0/9.0, 1.0/9.0, 1.0/9.0, 1.0/36.0, 1.0/36.0, 1.0/36.0, 1.0/36.0};
const int v_cx[9] = {0, 1, 0, -1, 0, 1, -1, -1, 1};
const int v_cy[9] = {0, 0, 1, 0, -1, 1, 1, -1, -1};
const int opp[9] = {0, 3, 4, 1, 2, 7, 8, 5, 6};

struct Cell {
    double f[9];
    bool obstacle;
};

// Pomocná funkce pro barevnou mapu (Jet-like)
void get_color(double v, double v_min, double v_max, unsigned char &r, unsigned char &g, unsigned char &b) {
    double norm = (v - v_min) / (v_max - v_min + 1e-9);
    norm = std::max(0.0, std::min(1.0, norm));
    r = static_cast<unsigned char>(255 * std::pow(norm, 0.4));
    g = static_cast<unsigned char>(255 * std::pow(norm, 1.5));
    b = static_cast<unsigned char>(255 * std::pow(norm, 3.0));
}

// Zápis výsledku do BMP souboru
void write_bmp(const std::string& filename, const std::vector<std::vector<double>>& speed) {
    double v_min = 1e10, v_max = -1e10;
    for (int i = 0; i < NX; ++i) {
        for (int j = 0; j < NY; ++j) {
            if (!std::isnan(speed[i][j])) {
                v_min = std::min(v_min, speed[i][j]);
                v_max = std::max(v_max, speed[i][j]);
            }
        }
    }
    unsigned char header[54] = {'B','M'};
    int filesize = 54 + 3 * NX * NY;
    header[2] = (unsigned char)(filesize); header[3] = (unsigned char)(filesize>>8);
    header[4] = (unsigned char)(filesize>>16); header[5] = (unsigned char)(filesize>>24);
    header[10] = 54; header[14] = 40;
    header[18] = (unsigned char)(NX); header[19] = (unsigned char)(NX>>8);
    header[20] = (unsigned char)(NX>>16); header[21] = (unsigned char)(NX>>24);
    header[22] = (unsigned char)(NY); header[23] = (unsigned char)(NY>>8);
    header[24] = (unsigned char)(NY>>16); header[25] = (unsigned char)(NY>>24);
    header[26] = 1; header[28] = 24;

    std::ofstream f(filename, std::ios::binary);
    f.write((char*)header, 54);
    for (int j = 0; j < NY; ++j) {
        for (int i = 0; i < NX; ++i) {
            unsigned char r, g, b_col;
            if (std::isnan(speed[i][j])) { r = g = b_col = 50; } // Věže budou šedé
            else { get_color(speed[i][j], v_min, v_max, r, g, b_col); }
            f.write((char*)&b_col, 1); f.write((char*)&g, 1); f.write((char*)&r, 1);
        }
        for (int p = 0; p < (4 - (NX * 3) % 4) % 4; ++p) f.put(0);
    }
}

int main() {
    std::cout << "Spousteni LBM simulace - věže mimo zákryt..." << std::endl;
    std::vector<std::vector<Cell>> grid(NX, std::vector<Cell>(NY));
    std::vector<std::vector<Cell>> next_grid(NX, std::vector<Cell>(NY));

    // --- GEOMETRIE: NATOČENÍ PROTI ZÁKRYTU ---
    double center_x = NX / 4.0;
    double center_y = NY / 2.0;
    double d_side = 60.0; // Polovina rozteče mezi věžemi
    double rad = 12.0;    // Poloměr věže
    double angle = 22.5 * (M_PI / 180.0); // Úhel rotace celého čtverce věží

    double tx[4], ty[4];
    for(int n = 0; n < 4; ++n) {
        // Souřadnice rohů čtverce před rotací
        double lx = (n == 0 || n == 3) ? d_side : -d_side;
        double ly = (n == 0 || n == 1) ? d_side : -d_side;
        // Aplikace rotační matice pro vyosení ze směru proudění (osa X)
        tx[n] = center_x + (lx * cos(angle) - ly * sin(angle));
        ty[n] = center_y + (lx * sin(angle) + ly * cos(angle));
    }

    // Inicializace polí a překážek
    for (int i = 0; i < NX; ++i) {
        for (int j = 0; j < NY; ++j) {
            bool obs = false;
            for(int n = 0; n < 4; ++n) {
                if (std::hypot(i - tx[n], j - ty[n]) < rad) { obs = true; break; }
            }
            grid[i][j].obstacle = obs;
            double rho = 1.0;
            for (int k = 0; k < 9; ++k) {
                double cu = 3.0 * (v_cx[k] * U_IN);
                grid[i][j].f[k] = w[k] * rho * (1.0 + cu + 0.5 * cu * cu - 1.5 * U_IN * U_IN);
            }
        }
    }

    // --- HLAVNÍ SMYČKA ---
    for (int step = 0; step < STEPS; ++step) {
        // 1. Streaming (přesun částic)
        for (int i = 0; i < NX; ++i) {
            for (int j = 0; j < NY; ++j) {
                for (int k = 0; k < 9; ++k) {
                    int ni = (i + v_cx[k] + NX) % NX;
                    int nj = (j + v_cy[k] + NY) % NY;
                    next_grid[ni][nj].f[k] = grid[i][j].f[k];
                }
            }
        }

        // 2. Kolize a okrajové podmínky
        for (int i = 0; i < NX; ++i) {
            for (int j = 0; j < NY; ++j) {
                if (grid[i][j].obstacle) {
                    // Bounce-back (odraz od překážky)
                    for (int k = 0; k < 9; ++k) grid[i][j].f[k] = next_grid[i][j].f[opp[k]];
                    continue;
                }

                double rho = 0, ux = 0, uy = 0;
                for (int k = 0; k < 9; ++k) {
                    rho += next_grid[i][j].f[k];
                    ux += next_grid[i][j].f[k] * v_cx[k];
                    uy += next_grid[i][j].f[k] * v_cy[k];
                }
                ux /= rho; uy /= rho;

                // Vstupní podmínka (Inlet) vlevo
                if (i == 0) { ux = U_IN; uy = 0; rho = 1.0; }

                // BGK Kolizní operátor
                for (int k = 0; k < 9; ++k) {
                    double cu = 3.0 * (v_cx[k] * ux + v_cy[k] * uy);
                    double feq = w[k] * rho * (1.0 + cu + 0.5 * cu * cu - 1.5 * (ux * ux + uy * uy));
                    grid[i][j].f[k] = next_grid[i][j].f[k] - (next_grid[i][j].f[k] - feq) / TAU;
                }
            }
        }
        if (step % 1000 == 0) std::cout << "Krok: " << step << " / " << STEPS << std::endl;
    }

    // Výpočet finální rychlosti a uložení
    std::vector<std::vector<double>> speed(NX, std::vector<double>(NY));
    for (int i = 0; i < NX; ++i) {
        for (int j = 0; j < NY; ++j) {
            if (grid[i][j].obstacle) speed[i][j] = std::nan("");
            else {
                double rho = 0, ux = 0, uy = 0;
                for (int k = 0; k < 9; ++k) {
                    rho += grid[i][j].f[k];
                    ux += grid[i][j].f[k] * v_cx[k];
                    uy += grid[i][j].f[k] * v_cy[k];
                }
                speed[i][j] = std::sqrt((ux/rho)*(ux/rho) + (uy/rho)*(uy/rho));
            }
        }
    }

    write_bmp("vysledek_bez_zakrytu.bmp", speed);
    std::cout << "Hotovo! Vysledek najdes v: vysledek_bez_zakrytu.bmp" << std::endl;
    return 0;
}
