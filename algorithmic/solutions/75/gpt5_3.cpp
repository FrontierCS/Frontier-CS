#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;

    int kB = b - 1;
    int kW = w - 1;
    int C = 2 * max(kB, kW) + 1; // enough columns for islands
    int R = 5;                   // fixed 5 rows
    
    vector<string> g(R, string(C, '.'));
    
    // Top part: white background
    // Row 0: all white (.)
    // Row 1: place black (@) islands separated by at least one white
    for (int i = 0; i < kB; ++i) {
        g[1][2 * i] = '@';
    }
    
    // Row 2: white barrier between top white area and bottom black area
    
    // Bottom part: black background
    // Row 3: all black (@)
    g[3].assign(C, '@');
    // Row 4: black background with white (.) islands separated by at least one black
    g[4].assign(C, '@');
    for (int i = 0; i < kW; ++i) {
        g[4][2 * i] = '.';
    }
    
    cout << R << " " << C << "\n";
    for (int i = 0; i < R; ++i) {
        cout << g[i] << "\n";
    }
    return 0;
}