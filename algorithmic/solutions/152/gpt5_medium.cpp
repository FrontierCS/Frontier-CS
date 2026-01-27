#include <bits/stdc++.h>
using namespace std;

struct Order {
    int a, b, c, d, id;
};

inline int manhattan(int x1, int y1, int x2, int y2) {
    return abs(x1 - x2) + abs(y1 - y2);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    const int N = 1000;
    const int M = 50;
    const int OX = 400, OY = 400;

    vector<Order> orders;
    orders.reserve(N);
    for (int i = 0; i < N; i++) {
        int a, b, c, d;
        if (!(cin >> a >> b >> c >> d)) return 0;
        orders.push_back({a, b, c, d, i});
    }

    // Select 50 orders with minimal estimated trip: office->pickup + pickup->delivery + delivery->office
    vector<pair<int, int>> score_idx; // (score, id)
    score_idx.reserve(N);
    for (int i = 0; i < N; i++) {
        int s = manhattan(OX, OY, orders[i].a, orders[i].b)
              + manhattan(orders[i].a, orders[i].b, orders[i].c, orders[i].d)
              + manhattan(orders[i].c, orders[i].d, OX, OY);
        score_idx.emplace_back(s, i);
    }
    nth_element(score_idx.begin(), score_idx.begin() + M, score_idx.end());
    score_idx.resize(M);
    // Extract selected indices
    vector<int> selectedIds;
    selectedIds.reserve(M);
    for (auto &p : score_idx) selectedIds.push_back(p.second);

    // Greedy route for pickups: start from office, visit nearest pickup
    vector<int> remainingPick = selectedIds;
    vector<int> pickupOrder;
    pickupOrder.reserve(M);
    int cx = OX, cy = OY;
    vector<char> usedPick(N, 0);
    for (int k = 0; k < M; k++) {
        int best = -1, bestDist = INT_MAX;
        for (int idx : remainingPick) {
            if (usedPick[idx]) continue;
            const auto &o = orders[idx];
            int d = manhattan(cx, cy, o.a, o.b);
            if (d < bestDist) {
                bestDist = d;
                best = idx;
            }
        }
        usedPick[best] = 1;
        pickupOrder.push_back(best);
        cx = orders[best].a;
        cy = orders[best].b;
    }

    // Greedy route for deliveries: start from last pickup position, visit nearest delivery
    vector<int> deliveryOrder;
    deliveryOrder.reserve(M);
    vector<char> usedDel(N, 0);
    for (int k = 0; k < M; k++) {
        int best = -1, bestDist = INT_MAX;
        for (int idx : selectedIds) {
            if (usedDel[idx]) continue;
            const auto &o = orders[idx];
            int d = manhattan(cx, cy, o.c, o.d);
            if (d < bestDist) {
                bestDist = d;
                best = idx;
            }
        }
        usedDel[best] = 1;
        deliveryOrder.push_back(best);
        cx = orders[best].c;
        cy = orders[best].d;
    }

    // Build route: start office, all pickups, all deliveries, end office
    vector<pair<int,int>> route;
    route.reserve(2 + 2*M);
    route.emplace_back(OX, OY);
    for (int idx : pickupOrder) {
        route.emplace_back(orders[idx].a, orders[idx].b);
    }
    for (int idx : deliveryOrder) {
        route.emplace_back(orders[idx].c, orders[idx].d);
    }
    route.emplace_back(OX, OY);

    // Output
    cout << M;
    for (int idx : selectedIds) cout << ' ' << (idx + 1);
    cout << '\n';

    cout << route.size();
    for (auto &p : route) cout << ' ' << p.first << ' ' << p.second;
    cout << '\n';

    return 0;
}