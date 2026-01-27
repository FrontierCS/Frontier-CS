#include <bits/stdc++.h>
using namespace std;

long long ceil_div(long long a, long long b) {
    return (a + b - 1) / b;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;
    
    int k_b = b - 1; // black islands in white stripe
    int k_w = w - 1; // white islands in black stripe
    
    int tw_min = (k_b > 0 ? 2 : 1);
    int tb_min = (k_w > 0 ? 2 : 1);
    int tw_max = (k_b > 0 ? 2 * k_b + 1 : 1);
    int tb_max = (k_w > 0 ? 2 * k_w + 1 : 1);
    
    long long bestScore = LLONG_MAX;
    int best_tw = -1, best_tb = -1, best_C = -1;
    
    for (int tw = tw_min; tw <= tw_max; ++tw) {
        int r_white = tw - 1; // usable rows for black islands
        for (int tb = tb_min; tb <= tb_max; ++tb) {
            int r_black = tb - 1; // usable rows for white islands
            
            long long Cb = (k_b == 0 ? 0 : ceil_div(2LL * k_b - 1, r_white));
            long long Cw = (k_w == 0 ? 0 : ceil_div(2LL * k_w - 1, r_black));
            long long C = max(1LL, max(Cb, Cw));
            
            // Connectivity safeguard: width 1 with >=3 rows and islands breaks base connectivity
            if (C == 1 && ((tb >= 3 && k_w > 0) || (tw >= 3 && k_b > 0))) continue;
            
            long long R = tw + tb;
            if (R * C > 100000LL) continue;
            
            long long score = ((long long)x * tb + (long long)y * tw) * C;
            if (score < bestScore) {
                bestScore = score;
                best_tw = tw;
                best_tb = tb;
                best_C = (int)C;
            }
        }
    }
    
    // Fallback to simple 4-row construction if somehow not found (should not happen)
    if (best_tw == -1) {
        int C = max(1, 2 * max(k_b, k_w) - 1);
        if ((k_b > 0 || k_w > 0) && C < 3) C = 3;
        if ((2 + 2) * 1 <= 100000 && C == 1) { best_tw = 2; best_tb = 2; best_C = 1; }
        else { best_tw = 2; best_tb = 2; best_C = C; }
    }
    
    int tw = best_tw, tb = best_tb, C = best_C;
    int R = tw + tb;
    vector<string> g(R, string(C, '?'));
    
    // Fill base colors
    for (int i = 0; i < tw; ++i) for (int j = 0; j < C; ++j) g[i][j] = '.';
    for (int i = tw; i < R; ++i) for (int j = 0; j < C; ++j) g[i][j] = '@';
    
    // Place black islands in white stripe (usable rows: 0 .. tw-2)
    int remB = k_b;
    for (int i = 0; i <= tw - 2 && remB > 0; ++i) {
        int s = i % 2;
        for (int j = s; j < C && remB > 0; j += 2) {
            g[i][j] = '@';
            --remB;
        }
    }
    
    // Place white islands in black stripe (usable rows: tw+1 .. R-1)
    int remW = k_w;
    for (int i = tw + 1; i <= R - 1 && remW > 0; ++i) {
        int s = (i - (tw + 1)) % 2;
        for (int j = s; j < C && remW > 0; j += 2) {
            g[i][j] = '.';
            --remW;
        }
    }
    
    cout << R << " " << C << "\n";
    for (int i = 0; i < R; ++i) {
        cout << g[i] << "\n";
    }
    
    return 0;
}