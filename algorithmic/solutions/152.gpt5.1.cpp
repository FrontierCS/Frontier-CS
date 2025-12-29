#include <bits/stdc++.h>
using namespace std;

long long manhattan(int x1, int y1, int x2, int y2) {
    return llabs(x1 - x2) + llabs(y1 - y2);
}

struct Order {
    int a, b, c, d;
    long long baseCost;
    int idx; // 1-based original index
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 1000;
    const int M = 50;
    const int CX = 400;
    const int CY = 400;

    vector<Order> orders;
    orders.reserve(N);

    for (int i = 0; i < N; i++) {
        int a, b, c, d;
        if (!(cin >> a >> b >> c >> d)) return 0;
        Order o;
        o.a = a; o.b = b; o.c = c; o.d = d;
        o.idx = i + 1;
        long long cost = 0;
        cost += manhattan(CX, CY, a, b);
        cost += manhattan(a, b, c, d);
        cost += manhattan(c, d, CX, CY);
        o.baseCost = cost;
        orders.push_back(o);
    }

    // Choose 50 orders with smallest baseCost
    sort(orders.begin(), orders.end(), [](const Order &x, const Order &y) {
        return x.baseCost < y.baseCost;
    });
    vector<Order> chosen(orders.begin(), orders.begin() + M);

    vector<int> rx(M), ry(M), dx(M), dy(M), orig_idx(M);
    for (int i = 0; i < M; i++) {
        rx[i] = chosen[i].a;
        ry[i] = chosen[i].b;
        dx[i] = chosen[i].c;
        dy[i] = chosen[i].d;
        orig_idx[i] = chosen[i].idx;
    }

    // Initial path by nearest neighbor heuristic on (restaurant) points
    vector<int> path(M);
    vector<bool> used(M, false);

    int start = 0;
    long long bestd = manhattan(CX, CY, rx[0], ry[0]);
    for (int i = 1; i < M; i++) {
        long long d = manhattan(CX, CY, rx[i], ry[i]);
        if (d < bestd) {
            bestd = d;
            start = i;
        }
    }
    path[0] = start;
    used[start] = true;
    for (int k = 1; k < M; k++) {
        int prev = path[k - 1];
        int bestj = -1;
        long long best = (1LL << 60);
        for (int j = 0; j < M; j++) {
            if (!used[j]) {
                long long d = manhattan(dx[prev], dy[prev], rx[j], ry[j]);
                if (d < best) {
                    best = d;
                    bestj = j;
                }
            }
        }
        path[k] = bestj;
        used[bestj] = true;
    }

    auto extCost = [&](const vector<int> &perm) -> long long {
        long long cost = 0;
        cost += manhattan(CX, CY, rx[perm[0]], ry[perm[0]]);
        for (int i = 0; i < M - 1; i++) {
            cost += manhattan(dx[perm[i]], dy[perm[i]], rx[perm[i + 1]], ry[perm[i + 1]]);
        }
        cost += manhattan(dx[perm[M - 1]], dy[perm[M - 1]], CX, CY);
        return cost;
    };

    long long bestExt = extCost(path);

    // Simple 2-opt (first improvement) with pass limit
    const int MAX_PASSES = 100;
    int passes = 0;
    while (passes < MAX_PASSES) {
        bool improved = false;
        for (int i = 0; i < M; i++) {
            for (int j = i + 1; j < M; j++) {
                vector<int> newPath = path;
                reverse(newPath.begin() + i, newPath.begin() + j + 1);
                long long c = extCost(newPath);
                if (c < bestExt) {
                    path.swap(newPath);
                    bestExt = c;
                    improved = true;
                    goto LOOP_END;
                }
            }
        }
    LOOP_END:
        if (!improved) break;
        passes++;
    }

    // Output
    // First line: m and chosen order indices (any order)
    cout << M;
    for (int i = 0; i < M; i++) {
        cout << " " << orig_idx[i];
    }
    cout << "\n";

    // Second line: n and route coordinates
    int n = 2 * M + 2;
    cout << n;
    // start at office
    cout << " " << CX << " " << CY;
    for (int k = 0; k < M; k++) {
        int p = path[k];
        cout << " " << rx[p] << " " << ry[p]; // restaurant
        cout << " " << dx[p] << " " << dy[p]; // destination
    }
    // return to office
    cout << " " << CX << " " << CY;
    cout << "\n";

    return 0;
}