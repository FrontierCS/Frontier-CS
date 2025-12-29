#include <bits/stdc++.h>
using namespace std;

static inline int manhattan(int x1, int y1, int x2, int y2) {
    return abs(x1 - x2) + abs(y1 - y2);
}

struct Order {
    int a, b, c, d;
    int id;
    int cost;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 1000;
    const int CX = 400, CY = 400;

    vector<Order> orders(N);
    for (int i = 0; i < N; i++) {
        cin >> orders[i].a >> orders[i].b >> orders[i].c >> orders[i].d;
        orders[i].id = i + 1;
        orders[i].cost = manhattan(CX, CY, orders[i].a, orders[i].b)
                       + manhattan(orders[i].a, orders[i].b, orders[i].c, orders[i].d)
                       + manhattan(orders[i].c, orders[i].d, CX, CY);
    }

    vector<int> idx(N);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int i, int j) {
        if (orders[i].cost != orders[j].cost) return orders[i].cost < orders[j].cost;
        return orders[i].id < orders[j].id;
    });

    const int M = 50;
    vector<int> chosen(idx.begin(), idx.begin() + M);

    // Greedy nearest-neighbor order for pickups
    vector<int> pickup_perm;
    pickup_perm.reserve(M);
    vector<char> used_pick(M, 0);
    int curx = CX, cury = CY;

    // Map local index -> global chosen index
    // We perform NN over the chosen set.
    vector<char> used_global(M, 0);
    for (int step = 0; step < M; step++) {
        int best_k = -1;
        int best_dist = INT_MAX;
        for (int k = 0; k < M; k++) {
            if (used_global[k]) continue;
            const auto &o = orders[chosen[k]];
            int d = manhattan(curx, cury, o.a, o.b);
            if (d < best_dist) {
                best_dist = d;
                best_k = k;
            }
        }
        used_global[best_k] = 1;
        pickup_perm.push_back(best_k);
        const auto &o = orders[chosen[best_k]];
        curx = o.a; cury = o.b;
    }

    // Greedy nearest-neighbor order for deliveries (after all pickups)
    vector<int> delivery_perm;
    delivery_perm.reserve(M);
    fill(used_global.begin(), used_global.end(), 0);
    for (int step = 0; step < M; step++) {
        int best_k = -1;
        int best_dist = INT_MAX;
        for (int k = 0; k < M; k++) {
            if (used_global[k]) continue;
            const auto &o = orders[chosen[k]];
            int d = manhattan(curx, cury, o.c, o.d);
            if (d < best_dist) {
                best_dist = d;
                best_k = k;
            }
        }
        used_global[best_k] = 1;
        delivery_perm.push_back(best_k);
        const auto &o = orders[chosen[best_k]];
        curx = o.c; cury = o.d;
    }

    vector<pair<int,int>> route;
    route.reserve(2 + 2 * M);
    route.push_back({CX, CY});
    for (int k : pickup_perm) {
        const auto &o = orders[chosen[k]];
        route.push_back({o.a, o.b});
    }
    for (int k : delivery_perm) {
        const auto &o = orders[chosen[k]];
        route.push_back({o.c, o.d});
    }
    route.push_back({CX, CY});

    // Output
    cout << M;
    for (int i = 0; i < M; i++) cout << ' ' << orders[chosen[i]].id;
    cout << "\n";

    cout << route.size();
    for (auto &p : route) cout << ' ' << p.first << ' ' << p.second;
    cout << "\n";

    return 0;
}