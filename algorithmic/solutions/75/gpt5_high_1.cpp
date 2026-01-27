#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;
    
    int a = b - 1; // black islands needed in white block
    int c = w - 1; // white islands needed in black block
    
    long long bestCost = LLONG_MAX;
    int best_p = 1, best_s0 = 1, best_s1 = 1, best_C = 1;
    
    int Pmax = max(1, max(a, c));
    for (int p = 1; p <= Pmax; ++p) {
        int s0 = 1 + (c > 0 ? (c + p - 1) / p : 0); // ceil(c/p) + 1
        int s1 = 1 + (a > 0 ? (a + p - 1) / p : 0); // ceil(a/p) + 1
        long long C = 2LL * p - 1;
        if (a > 0 || c > 0) {
            if (C < 2) C = 2; // ensure connectivity when islands exist
        } else {
            // both zero -> single column is fine
        }
        long long cost = C * (1LL * x * (2 * s0 - 1) + 1LL * y * (2 * s1 - 1));
        if (cost < bestCost) {
            bestCost = cost;
            best_p = p;
            best_s0 = s0;
            best_s1 = s1;
            best_C = (int)C;
        } else if (cost == bestCost) {
            long long RB = 2 * s0 - 1;
            long long RW = 2 * s1 - 1;
            long long R = RB + RW;
            long long bestRB = 2 * best_s0 - 1;
            long long bestRW = 2 * best_s1 - 1;
            long long bestArea = (bestRB + bestRW) * 1LL * best_C;
            long long area = R * 1LL * C;
            if (area < bestArea) {
                best_p = p;
                best_s0 = s0;
                best_s1 = s1;
                best_C = (int)C;
            }
        }
    }
    
    int s0 = best_s0, s1 = best_s1, C = best_C;
    int RB = 2 * s0 - 1;
    int RW = 2 * s1 - 1;
    int R = RB + RW;
    
    vector<string> grid(R, string(C, '@'));
    for (int i = RB; i < R; ++i) {
        fill(grid[i].begin(), grid[i].end(), '.');
    }
    
    int needW = c; // white islands in black block
    for (int i = 1; i <= RB - 2 && needW > 0; i += 2) {
        for (int j = 0; j < C && needW > 0; j += 2) {
            grid[i][j] = '.';
            --needW;
        }
    }
    
    int needB = a; // black islands in white block
    for (int i = RB + 1; i <= RB + RW - 2 && needB > 0; i += 2) {
        for (int j = 0; j < C && needB > 0; j += 2) {
            grid[i][j] = '@';
            --needB;
        }
    }
    
    cout << R << " " << C << "\n";
    for (int i = 0; i < R; ++i) {
        cout << grid[i] << "\n";
    }
    return 0;
}