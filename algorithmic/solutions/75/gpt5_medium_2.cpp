#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;
    
    int B = b - 1; // black islands needed
    int W = w - 1; // white islands needed
    
    int m = max(B, W);
    int c = max(1, m);
    int cap1 = (c + 1) / 2; // capacity per single island row
    
    int a; // number of white-in-black island rows
    if (W == 0) a = 0;
    else if (W <= cap1) a = 1;
    else a = 2;
    
    int d; // number of black-in-white island rows
    if (B == 0) d = 0;
    else if (B <= cap1) d = 1;
    else d = 2;
    
    int r = a + 1 + 1 + d; // island rows in black section + solid black + solid white + island rows in white section
    
    vector<string> grid(r, string(c, '@'));
    // Initialize black section
    for (int i = 0; i < a + 1; ++i) {
        grid[i] = string(c, '@');
    }
    // Solid white row
    grid[a + 1] = string(c, '.');
    // White section island rows (base '.')
    for (int i = a + 2; i < r; ++i) {
        grid[i] = string(c, '.');
    }
    
    // Place white islands in black section
    int remW = W;
    if (a >= 1) {
        for (int col = 0; col < c && remW > 0; col += 2) {
            grid[0][col] = '.';
            remW--;
        }
    }
    if (a >= 2) {
        for (int col = 1; col < c && remW > 0; col += 2) {
            grid[1][col] = '.';
            remW--;
        }
    }
    
    // Place black islands in white section
    int remB = B;
    if (d >= 1) {
        int row = a + 2;
        for (int col = 0; col < c && remB > 0; col += 2) {
            grid[row][col] = '@';
            remB--;
        }
    }
    if (d >= 2) {
        int row = a + 3;
        for (int col = 1; col < c && remB > 0; col += 2) {
            grid[row][col] = '@';
            remB--;
        }
    }
    
    cout << r << " " << c << "\n";
    for (int i = 0; i < r; ++i) {
        cout << grid[i] << "\n";
    }
    return 0;
}