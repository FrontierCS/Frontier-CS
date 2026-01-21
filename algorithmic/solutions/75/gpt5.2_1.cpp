#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;

    int kW = w - 1; // white dots in black region
    int kB = b - 1; // black dots in white region

    long long bestCost = (1LL << 62);
    int bestC = -1, bestHb = -1, bestHw = -1;

    for (int C = 1; C <= 100000; C++) {
        if (1LL * C > 100000) break;

        if (C == 1 && (kW > 1 || kB > 1)) continue; // would disconnect base components

        int colpos = (C + 1) / 2;

        auto minHeight = [&](int k) -> int {
            if (k <= 0) return 1;
            int reqRows = (k + colpos - 1) / colpos;
            return 2 * reqRows;
        };

        int Hb = minHeight(kW);
        int Hw = minHeight(kB);

        long long R = 1LL * Hb + Hw;
        long long area = R * C;
        if (R < 1 || R > 100000) continue;
        if (area > 100000) continue;

        long long black = 1LL * Hb * C + (b - w);
        long long white = area - black;
        if (black < 0 || white < 0) continue;

        long long cost = 1LL * x * black + 1LL * y * white;
        if (cost < bestCost) {
            bestCost = cost;
            bestC = C;
            bestHb = Hb;
            bestHw = Hw;
        }
    }

    if (bestC == -1) {
        // Fallback (should never happen for given constraints)
        bestC = 2000;
        int colpos = (bestC + 1) / 2;
        auto minHeight = [&](int k) -> int {
            if (k <= 0) return 1;
            int reqRows = (k + colpos - 1) / colpos;
            return 2 * reqRows;
        };
        bestHb = minHeight(kW);
        bestHw = minHeight(kB);
        while (1LL * (bestHb + bestHw) * bestC > 100000) bestC--;
    }

    int C = bestC;
    int Hb = bestHb;
    int Hw = bestHw;
    int R = Hb + Hw;

    vector<string> grid(R);
    for (int i = 0; i < R; i++) {
        grid[i] = string(C, (i < Hb) ? '@' : '.');
    }

    int need = kW;
    for (int i = 0; i < Hb - 1 && need > 0; i += 2) {
        for (int j = 0; j < C && need > 0; j += 2) {
            grid[i][j] = '.';
            --need;
        }
    }

    need = kB;
    for (int i = Hb + 1; i < R && need > 0; i += 2) {
        for (int j = 0; j < C && need > 0; j += 2) {
            grid[i][j] = '@';
            --need;
        }
    }

    cout << R << ' ' << C << "\n";
    for (int i = 0; i < R; i++) cout << grid[i] << "\n";
    return 0;
}