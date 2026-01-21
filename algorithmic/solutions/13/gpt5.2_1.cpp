#include <bits/stdc++.h>
using namespace std;

static const int T = 3000;

static inline int idx(int x, int y) {
    return (x - 1) * T + (y - 1);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int sx, sy;
    if (!(cin >> sx >> sy)) return 0;

    vector<unsigned char> black((size_t)T * (size_t)T, 0);

    auto isBlack = [&](int x, int y) -> bool {
        if (x < 1 || x > T || y < 1 || y > T) return false;
        return black[idx(x, y)] != 0;
    };
    auto setBlack = [&](int x, int y) {
        if (x < 1 || x > T || y < 1 || y > T) return;
        black[idx(x, y)] = 1;
    };

    int rx = sx, ry = sy;

    int scanPtr = 0; // linear index into [0..T*T)

    auto nextUnusedCell = [&]() -> pair<int,int> {
        while (scanPtr < T * T && black[scanPtr]) scanPtr++;
        if (scanPtr >= T * T) return {1, 1};
        int x = scanPtr / T + 1;
        int y = scanPtr % T + 1;
        return {x, y};
    };

    for (int turn = 1; turn <= T; turn++) {
        vector<pair<int,int>> neigh;
        neigh.reserve(8);
        for (int dx = -1; dx <= 1; dx++) {
            for (int dy = -1; dy <= 1; dy++) {
                if (dx == 0 && dy == 0) continue;
                int nx = rx + dx, ny = ry + dy;
                if (nx <= 0 || ny <= 0) continue;
                neigh.push_back({nx, ny});
            }
        }

        vector<pair<int,int>> safeInRange;
        safeInRange.reserve(8);
        for (auto [nx, ny] : neigh) {
            if (1 <= nx && nx <= T && 1 <= ny && ny <= T && !isBlack(nx, ny)) {
                safeInRange.push_back({nx, ny});
            }
        }

        int mx = 1, my = 1;

        if (safeInRange.empty()) {
            auto p = nextUnusedCell();
            mx = p.first; my = p.second;
        } else if ((int)safeInRange.size() == 1) {
            mx = safeInRange[0].first;
            my = safeInRange[0].second;
        } else {
            // Mine the "most outward" safe neighbor to discourage escaping.
            long long bestScore = LLONG_MIN;
            pair<int,int> best = safeInRange[0];
            for (auto [nx, ny] : safeInRange) {
                long long score = 1LL * (nx + ny) * 1000000LL + 1LL * max(nx, ny) * 1000LL + nx;
                if (score > bestScore) {
                    bestScore = score;
                    best = {nx, ny};
                }
            }
            mx = best.first;
            my = best.second;
        }

        // Ensure within bounds; fallback if something went wrong.
        if (!(1 <= mx && mx <= T && 1 <= my && my <= T)) {
            auto p = nextUnusedCell();
            mx = p.first; my = p.second;
        }

        cout << mx << ' ' << my << '\n';
        cout.flush();
        setBlack(mx, my);

        int nx, ny;
        if (!(cin >> nx >> ny)) return 0;
        if (nx == 0 && ny == 0) return 0;

        rx = nx;
        ry = ny;
    }

    return 0;
}