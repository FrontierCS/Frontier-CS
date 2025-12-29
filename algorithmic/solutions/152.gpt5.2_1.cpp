#include <bits/stdc++.h>
using namespace std;

struct Order {
    int a, b, c, d;
};

static inline int manhattan(int x1, int y1, int x2, int y2) {
    return abs(x1 - x2) + abs(y1 - y2);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 1000;
    vector<Order> ord(N);
    for (int i = 0; i < N; i++) {
        cin >> ord[i].a >> ord[i].b >> ord[i].c >> ord[i].d;
    }

    const int ox = 400, oy = 400;

    vector<pair<int,int>> scored;
    scored.reserve(N);
    for (int i = 0; i < N; i++) {
        int base = manhattan(ox, oy, ord[i].a, ord[i].b)
                 + manhattan(ord[i].a, ord[i].b, ord[i].c, ord[i].d)
                 + manhattan(ord[i].c, ord[i].d, ox, oy);
        scored.push_back({base, i});
    }
    sort(scored.begin(), scored.end());

    const int M = 50;
    vector<int> cand;
    cand.reserve(M);
    for (int i = 0; i < M; i++) cand.push_back(scored[i].second);

    // Greedy reordering to reduce travel (deliver immediately after pickup).
    vector<char> used(N, 0);
    vector<int> route_orders;
    route_orders.reserve(M);

    int cx = ox, cy = oy;
    for (int step = 0; step < M; step++) {
        int bestIdx = -1;
        int bestCost = INT_MAX;
        for (int idx : cand) {
            if (used[idx]) continue;
            const auto &o = ord[idx];
            int cost = manhattan(cx, cy, o.a, o.b) + manhattan(o.a, o.b, o.c, o.d);
            if (cost < bestCost) {
                bestCost = cost;
                bestIdx = idx;
            }
        }
        used[bestIdx] = 1;
        route_orders.push_back(bestIdx);
        cx = ord[bestIdx].c;
        cy = ord[bestIdx].d;
    }

    // Build point sequence
    vector<pair<int,int>> pts;
    pts.reserve(2 * M + 2);
    pts.push_back({ox, oy});
    for (int idx : route_orders) {
        pts.push_back({ord[idx].a, ord[idx].b});
        pts.push_back({ord[idx].c, ord[idx].d});
    }
    pts.push_back({ox, oy});

    // Output
    cout << M;
    for (int idx : route_orders) cout << ' ' << (idx + 1);
    cout << "\n";

    cout << pts.size();
    for (auto [x, y] : pts) cout << ' ' << x << ' ' << y;
    cout << "\n";

    return 0;
}