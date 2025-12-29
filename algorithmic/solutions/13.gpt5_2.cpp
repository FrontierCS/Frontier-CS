#include <bits/stdc++.h>
using namespace std;

static const int T_LIMIT = 3000;

inline bool inRange(int x, int y) {
    return 1 <= x && x <= T_LIMIT && 1 <= y && y <= T_LIMIT;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int rx, ry;
    if (!(cin >> rx >> ry)) {
        return 0;
    }

    auto key = [](int x, int y)->long long {
        return (long long)x * 4005 + y;
    };

    unordered_set<long long> painted;
    painted.reserve(100000);
    painted.max_load_factor(0.7);

    auto paint_and_flush = [&](int x, int y) {
        cout << x << " " << y << "\n";
        cout.flush();
    };

    auto try_paint = [&](int x, int y)->bool {
        if (!inRange(x, y)) return false;
        long long k = key(x, y);
        if (painted.find(k) != painted.end()) return false;
        painted.insert(k);
        paint_and_flush(x, y);
        return true;
    };

    // Track trap progress for each x target
    // trap order: (X,1), (X-1,1), (X+1,1), (X-1,2), (X,2), (X+1,2)
    // We'll mark which indices are already painted
    struct TrapState {
        array<bool,6> done{};
    };
    unordered_map<int, TrapState> trap;
    trap.reserve(10000);
    trap.max_load_factor(0.7);

    auto trap_cells = [&](int X)->array<pair<int,int>,6> {
        array<pair<int,int>,6> a;
        a[0] = {X, 1};
        a[1] = {X-1, 1};
        a[2] = {X+1, 1};
        a[3] = {X-1, 2};
        a[4] = {X, 2};
        a[5] = {X+1, 2};
        return a;
    };

    auto build_trap_step = [&](int X)->bool {
        if (X < 2) X = 2;
        if (X > T_LIMIT-1) X = T_LIMIT - 1;
        auto &st = trap[X];
        auto cells = trap_cells(X);
        for (int i = 0; i < 6; ++i) {
            if (st.done[i]) continue;
            auto [cx, cy] = cells[i];
            if (!inRange(cx, cy)) { st.done[i] = true; continue; }
            long long k = key(cx, cy);
            if (painted.find(k) != painted.end()) { st.done[i] = true; continue; }
            painted.insert(k);
            st.done[i] = true;
            paint_and_flush(cx, cy);
            return true;
        }
        return false;
    };

    int steps = 0;
    while (steps < T_LIMIT) {
        // Choose a cell to paint trying to limit upward movement first
        bool painted_now = false;

        // 1) Try to block direct upward moves around current robot position
        // Prefer center then sides
        int ux[3] = {rx, rx-1, rx+1};
        int uy[3] = {ry+1, ry+1, ry+1};
        for (int i = 0; i < 3 && !painted_now; ++i) {
            if (try_paint(ux[i], uy[i])) {
                painted_now = true;
            }
        }

        // 2) If not painted, build/add a trap near row 1 for current rx
        if (!painted_now) {
            int X = rx;
            if (!build_trap_step(X)) {
                // Try neighboring x to widen trap coverage
                bool ok = false;
                for (int delta = 1; delta <= 3 && !ok; ++delta) {
                    if (build_trap_step(max(2, min(T_LIMIT-1, rx - delta)))) ok = true;
                    else if (build_trap_step(max(2, min(T_LIMIT-1, rx + delta)))) ok = true;
                }
                if (!ok) {
                    // Fallback: paint somewhere harmless near bottom
                    for (int t = 1; t <= 5 && !ok; ++t) {
                        int px = max(1, min(T_LIMIT, rx + t));
                        int py = 1;
                        if (try_paint(px, py)) ok = true;
                    }
                    if (!ok) {
                        // As a last resort, paint (1,1)
                        if (!try_paint(1, 1)) {
                            // If even that is painted, paint rx,2 or rx,1 if possible
                            if (!try_paint(rx, 2)) {
                                try_paint(rx, 1);
                            }
                        }
                    }
                }
            }
        }

        steps++;

        int nx, ny;
        if (!(cin >> nx >> ny)) {
            return 0;
        }
        if (nx == 0 && ny == 0) {
            return 0;
        }
        rx = nx; ry = ny;
    }

    return 0;
}