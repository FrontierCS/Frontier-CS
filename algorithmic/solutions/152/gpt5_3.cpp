#include <bits/stdc++.h>
using namespace std;

struct Order {
    int a, b, c, d;
};

inline long long mdist(int x1, int y1, int x2, int y2) {
    return llabs(x1 - x2) + llabs(y1 - y2);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    const int CENTER_X = 400, CENTER_Y = 400;

    vector<Order> orders;
    orders.reserve(1000);
    for (int i = 0; i < 1000; i++) {
        int a, b, c, d;
        if (!(cin >> a >> b >> c >> d)) break;
        orders.push_back({a, b, c, d});
    }
    int N = (int)orders.size();
    int M = min(50, N);

    // Greedy selection of 50 orders
    vector<bool> used(N, false);
    vector<int> chosen;
    chosen.reserve(M);
    int currx = CENTER_X, curry = CENTER_Y;

    for (int t = 0; t < M; t++) {
        long long bestInc = (1LL<<60);
        long long bestLoop = (1LL<<60);
        long long bestRet = (1LL<<60);
        int bestIdx = -1;
        for (int i = 0; i < N; i++) {
            if (used[i]) continue;
            const auto &o = orders[i];
            long long inc = mdist(currx, curry, o.a, o.b) + mdist(o.a, o.b, o.c, o.d);
            long long loop = mdist(CENTER_X, CENTER_Y, o.a, o.b) + mdist(o.a, o.b, o.c, o.d) + mdist(o.c, o.d, CENTER_X, CENTER_Y);
            long long dret = mdist(o.c, o.d, CENTER_X, CENTER_Y);
            if (inc < bestInc || (inc == bestInc && (loop < bestLoop || (loop == bestLoop && dret < bestRet)))) {
                bestInc = inc;
                bestLoop = loop;
                bestRet = dret;
                bestIdx = i;
            }
        }
        if (bestIdx == -1) break;
        used[bestIdx] = true;
        chosen.push_back(bestIdx);
        currx = orders[bestIdx].c;
        curry = orders[bestIdx].d;
    }

    // If somehow less than M selected (shouldn't happen), fill with any remaining
    for (int i = 0; (int)chosen.size() < M && i < N; i++) {
        if (!used[i]) {
            used[i] = true;
            chosen.push_back(i);
        }
    }

    int m = (int)chosen.size();
    if (m == 0) {
        // Fallback: choose at least one if no orders read
        cout << 0 << "\n";
        cout << 2 << " " << CENTER_X << " " << CENTER_Y << " " << CENTER_X << " " << CENTER_Y << "\n";
        return 0;
    }

    // 2-opt on order sequence to minimize cross edges (center->a[0], c[i]->a[i+1], c[last]->center)
    auto A = vector<pair<int,int>>(N), C = vector<pair<int,int>>(N);
    for (int i = 0; i < N; i++) {
        A[i] = {orders[i].a, orders[i].b};
        C[i] = {orders[i].c, orders[i].d};
    }
    auto distPair = [&](const pair<int,int>& p, const pair<int,int>& q) -> long long {
        return mdist(p.first, p.second, q.first, q.second);
    };
    pair<int,int> center = {CENTER_X, CENTER_Y};

    bool improved = true;
    while (improved) {
        improved = false;
        for (int l = 0; l < m; l++) {
            for (int r = l + 1; r < m; r++) {
                pair<int,int> prevC = (l == 0) ? center : C[chosen[l - 1]];
                pair<int,int> nextA = (r + 1 == m) ? center : A[chosen[r + 1]];
                long long before = 0, after = 0;

                before += distPair(prevC, A[chosen[l]]);
                for (int k = l; k <= r - 1; k++) before += distPair(C[chosen[k]], A[chosen[k + 1]]);
                before += distPair(C[chosen[r]], nextA);

                after += distPair(prevC, A[chosen[r]]);
                for (int k = l + 1; k <= r; k++) after += distPair(C[chosen[k]], A[chosen[k - 1]]);
                after += distPair(C[chosen[l]], nextA);

                if (after + 0 < before) {
                    reverse(chosen.begin() + l, chosen.begin() + r + 1);
                    improved = true;
                    goto next_iter;
                }
            }
        }
        next_iter: ;
    }

    // Build route: start at center, for each order visit a then c, end at center
    vector<pair<int,int>> route;
    route.reserve(2 * m + 2);
    auto pushPoint = [&](int x, int y) {
        if (route.empty() || route.back().first != x || route.back().second != y) {
            route.emplace_back(x, y);
        }
    };
    pushPoint(CENTER_X, CENTER_Y);
    for (int idx : chosen) {
        pushPoint(orders[idx].a, orders[idx].b);
        pushPoint(orders[idx].c, orders[idx].d);
    }
    pushPoint(CENTER_X, CENTER_Y);

    // Output
    cout << m;
    for (int i = 0; i < m; i++) cout << " " << (chosen[i] + 1);
    cout << "\n";
    cout << (int)route.size();
    for (auto &p : route) cout << " " << p.first << " " << p.second;
    cout << "\n";
    return 0;
}