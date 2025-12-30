#include <bits/stdc++.h>
using namespace std;

int main() {
    string S;
    for (int n = 1; S.size() < 112; ++n) {
        S += to_string(n);
    }
    char grid[8][14];
    int idx = 0;
    for (int r = 0; r < 8; ++r) {
        if (r % 2 == 0) {
            for (int c = 0; c < 14; ++c) {
                grid[r][c] = S[idx++];
            }
        } else {
            for (int c = 13; c >= 0; --c) {
                grid[r][c] = S[idx++];
            }
        }
    }
    for (int r = 0; r < 8; ++r) {
        for (int c = 0; c < 14; ++c) {
            cout << grid[r][c];
        }
        cout << '\n';
    }
    return 0;
}