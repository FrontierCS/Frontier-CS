#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    // Build a snake traversal over 8x14.
    vector<pair<int,int>> path;
    path.reserve(8 * 14);
    for (int r = 0; r < 8; r++) {
        if (r % 2 == 0) {
            for (int c = 0; c < 14; c++) path.push_back({r, c});
        } else {
            for (int c = 13; c >= 0; c--) path.push_back({r, c});
        }
    }

    // Random symmetries to avoid a fixed predetermined output.
    bool flipH = (rng() & 1);
    bool flipV = (rng() & 1);
    bool revPath = (rng() & 1);

    auto mapPos = [&](pair<int,int> p) -> pair<int,int> {
        int r = p.first, c = p.second;
        if (flipH) c = 13 - c;
        if (flipV) r = 7 - r;
        return {r, c};
    };

    if (revPath) reverse(path.begin(), path.end());

    // Create digit stream as concatenation of 1..N, where N is maximal fitting into 112 cells.
    string seq;
    int N = 0;
    while (true) {
        int nxt = N + 1;
        string t = to_string(nxt);
        if ((int)seq.size() + (int)t.size() > 112) break;
        seq += t;
        N = nxt;
    }

    vector<string> grid(8, string(14, '0'));

    // Fill along the snake with seq, remaining with random digits.
    for (int i = 0; i < 112; i++) {
        char ch;
        if (i < (int)seq.size()) ch = seq[i];
        else ch = char('0' + (int)(rng() % 10));
        auto [r, c] = mapPos(path[i]);
        grid[r][c] = ch;
    }

    for (int r = 0; r < 8; r++) {
        cout << grid[r] << "\n";
    }
    return 0;
}