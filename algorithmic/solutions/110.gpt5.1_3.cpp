#include <bits/stdc++.h>
using namespace std;

int main() {
    const int H = 8;
    const int W = 14;
    const int N = H * W;

    string S;
    int x = 1;
    while (true) {
        string t = to_string(x);
        if (S.size() + t.size() <= (size_t)N) {
            S += t;
            ++x;
        } else {
            break;
        }
    }
    while (S.size() < (size_t)N) S += '0';

    vector<string> grid(H, string(W, '0'));
    int idx = 0;
    for (int r = 0; r < H; ++r) {
        if (r % 2 == 0) {
            for (int c = 0; c < W; ++c) {
                grid[r][c] = S[idx++];
            }
        } else {
            for (int c = W - 1; c >= 0; --c) {
                grid[r][c] = S[idx++];
            }
        }
    }

    for (int r = 0; r < H; ++r) {
        cout << grid[r] << '\n';
    }

    return 0;
}