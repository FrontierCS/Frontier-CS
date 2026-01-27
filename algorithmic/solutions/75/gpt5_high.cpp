#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;

    int kB = b - 1; // number of black islands in white sea
    int kW = w - 1; // number of white islands in black sea

    auto needWidth = [](int k) {
        return (k == 0) ? 1 : (2 * k - 1);
    };

    int width = max(needWidth(kB), needWidth(kW));
    width = max(1, width);
    int rows = 4;

    vector<string> grid(rows, string(width, '.'));
    // Row 1: white sea with black islands
    for (int i = 0; i < kB; ++i) {
        int col = 2 * i;
        if (col < width) grid[0][col] = '@';
    }
    // Row 2: white sea (all '.')
    // already initialized

    // Row 3: black sea (all '@')
    for (int j = 0; j < width; ++j) grid[2][j] = '@';

    // Row 4: black sea with white islands
    for (int j = 0; j < width; ++j) grid[3][j] = '@';
    for (int i = 0; i < kW; ++i) {
        int col = 2 * i;
        if (col < width) grid[3][col] = '.';
    }

    cout << rows << " " << width << "\n";
    for (int i = 0; i < rows; ++i) {
        cout << grid[i] << "\n";
    }

    return 0;
}