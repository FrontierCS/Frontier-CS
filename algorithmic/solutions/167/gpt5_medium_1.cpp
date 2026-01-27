#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    unordered_set<long long> S;
    S.reserve(2 * N * 2);
    S.max_load_factor(0.7f);
    auto enc = [](int x, int y) -> long long {
        return (static_cast<long long>(x) << 20) ^ y;
    };
    for (int i = 0; i < 2 * N; ++i) {
        int x, y;
        cin >> x >> y;
        S.insert(enc(x, y));
    }

    auto ok_square = [&](int x, int y) -> bool {
        // Check four corners (x,y), (x+1,y), (x,y+1), (x+1,y+1)
        if (x < 0 || x + 1 > 100000 || y < 0 || y + 1 > 100000) return false;
        if (S.find(enc(x, y)) != S.end()) return false;
        if (S.find(enc(x + 1, y)) != S.end()) return false;
        if (S.find(enc(x, y + 1)) != S.end()) return false;
        if (S.find(enc(x + 1, y + 1)) != S.end()) return false;
        return true;
    };

    int fx = -1, fy = -1;

    // First, try a small region near (0,0)
    for (int x = 0; x <= 1000 && fx == -1; ++x) {
        for (int y = 0; y <= 1000; ++y) {
            if (ok_square(x, y)) { fx = x; fy = y; break; }
        }
    }

    // If not found (extremely unlikely), try a few more regions
    if (fx == -1) {
        // Try corners of the whole area
        vector<pair<int,int>> cand = {
            {0,0}, {0,99999}, {99999,0}, {99999,99999},
            {50000,50000}, {20000,20000}, {80000,80000},
            {1000,50000}, {50000,1000}, {99000,99000}
        };
        for (auto [cx, cy] : cand) {
            int x = max(0, min(99999, cx));
            int y = max(0, min(99999, cy));
            // Adjust to be within bounds for x+1, y+1
            if (x == 100000) x = 99999;
            if (y == 100000) y = 99999;
            if (ok_square(x, y)) { fx = x; fy = y; break; }
        }
    }

    // As last resort, random search
    if (fx == -1) {
        mt19937 rng(712367);
        uniform_int_distribution<int> dist(0, 99999);
        for (int t = 0; t < 200000 && fx == -1; ++t) {
            int x = dist(rng);
            int y = dist(rng);
            if (x == 100000) x = 99999;
            if (y == 100000) y = 99999;
            if (ok_square(x, y)) { fx = x; fy = y; break; }
        }
    }

    // Fallback to (0,0) if still not found (should not happen)
    if (fx == -1) { fx = 0; fy = 0; }

    // Output rectangle with 4 vertices
    cout << 4 << '\n';
    cout << fx << ' ' << fy << '\n';
    cout << fx + 1 << ' ' << fy << '\n';
    cout << fx + 1 << ' ' << fy + 1 << '\n';
    cout << fx << ' ' << fy + 1 << '\n';

    return 0;
}