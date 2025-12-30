#include <bits/stdc++.h>
using namespace std;

static const int N = 30;
struct Edge { int px, py, cx, cy; };

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<vector<int>> g(N);
    for (int x = 0; x < N; ++x) {
        g[x].resize(x + 1);
        for (int y = 0; y <= x; ++y) {
            if (!(cin >> g[x][y])) return 0;
        }
    }

    const int K_LIMIT = 10000;
    vector<array<int,4>> ops;
    ops.reserve(K_LIMIT);

    auto doSwap = [&](int x1, int y1, int x2, int y2)->bool {
        if ((int)ops.size() >= K_LIMIT) return false;
        // Ensure adjacency implicitly by only calling for valid pairs
        ops.push_back({x1, y1, x2, y2});
        swap(g[x1][y1], g[x2][y2]);
        return true;
    };

    auto siftDownFrom = [&](int sx, int sy) {
        int x = sx, y = sy;
        while (x < N-1) {
            int v = g[x][y];
            int va = g[x+1][y];
            int vb = g[x+1][y+1];
            if (v <= va && v <= vb) break;
            if (va < vb) {
                if (!doSwap(x, y, x+1, y)) return;
                x = x + 1; // y unchanged
            } else {
                if (!doSwap(x, y, x+1, y+1)) return;
                x = x + 1; y = y + 1;
            }
        }
    };

    auto siftUpFrom = [&](int sx, int sy) {
        int x = sx, y = sy;
        while (x > 0) {
            int v = g[x][y];
            int best_px = -1, best_py = -1, best_val = INT_MIN;
            // parent (x-1, y)
            if (y <= x-1) {
                int pv = g[x-1][y];
                if (pv > v && pv > best_val) {
                    best_val = pv; best_px = x-1; best_py = y;
                }
            }
            // parent (x-1, y-1)
            if (y > 0) {
                int pv = g[x-1][y-1];
                if (pv > v && pv > best_val) {
                    best_val = pv; best_px = x-1; best_py = y-1;
                }
            }
            if (best_px == -1) break;
            if (!doSwap(best_px, best_py, x, y)) return;
            x = best_px; y = best_py;
        }
    };

    // Build edge list
    vector<Edge> edges;
    edges.reserve(N*(N-1));
    for (int x = 0; x < N-1; ++x) {
        for (int y = 0; y <= x; ++y) {
            edges.push_back({x,y,x+1,y});
            edges.push_back({x,y,x+1,y+1});
        }
    }

    auto calcE = [&]() -> int {
        int E = 0;
        for (auto &e : edges) {
            if (g[e.px][e.py] > g[e.cx][e.cy]) ++E;
        }
        return E;
    };

    // Phase 1: multiple top-down sift-down passes
    // Reserve some operations for phase 2
    const int reserve_for_phase2 = 3500;
    while ((int)ops.size() < K_LIMIT - reserve_for_phase2) {
        bool any = false;
        for (int x = 0; x < N-1; ++x) {
            for (int y = 0; y <= x; ++y) {
                int before_ops = (int)ops.size();
                siftDownFrom(x, y);
                if ((int)ops.size() > before_ops) any = true;
                if ((int)ops.size() >= K_LIMIT - reserve_for_phase2) break;
            }
            if ((int)ops.size() >= K_LIMIT - reserve_for_phase2) break;
        }
        if (!any) break;
        // Optional early stop if already perfect
        if (calcE() == 0) break;
    }

    // Phase 2: greedy elimination of remaining inversions with local sifts
    while ((int)ops.size() < K_LIMIT) {
        int bestDiff = 0;
        int bestIdx = -1;
        for (int i = 0; i < (int)edges.size(); ++i) {
            auto &e = edges[i];
            int diff = g[e.px][e.py] - g[e.cx][e.cy];
            if (diff > bestDiff) {
                bestDiff = diff;
                bestIdx = i;
            }
        }
        if (bestIdx == -1) break; // E == 0
        
        auto e = edges[bestIdx];
        if (!doSwap(e.px, e.py, e.cx, e.cy)) break;

        // After swap, a smaller value moved to (e.px,e.py), larger moved to (e.cx,e.cy)
        // Try to move the small one up and large one down
        if ((int)ops.size() < K_LIMIT) {
            siftUpFrom(e.px, e.py);
        }
        if ((int)ops.size() < K_LIMIT) {
            siftDownFrom(e.cx, e.cy);
        }
    }

    // Output
    cout << ops.size() << '\n';
    for (auto &op : ops) {
        cout << op[0] << ' ' << op[1] << ' ' << op[2] << ' ' << op[3] << '\n';
    }
    return 0;
}