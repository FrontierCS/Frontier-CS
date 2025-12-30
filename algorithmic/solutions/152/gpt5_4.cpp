#include <bits/stdc++.h>
using namespace std;

struct Order {
    int a, b, c, d;
    int id; // 1-based
    long long loopCost;
};

static inline int manhattan(int x1, int y1, int x2, int y2) {
    return abs(x1 - x2) + abs(y1 - y2);
}

long long routeCost(const vector<int>& seq, const vector<Order>& orders) {
    const int OX = 400, OY = 400;
    long long cost = 0;
    int x = OX, y = OY;
    for (int idx : seq) {
        const Order& o = orders[idx];
        cost += manhattan(x, y, o.a, o.b);
        cost += manhattan(o.a, o.b, o.c, o.d);
        x = o.c; y = o.d;
    }
    cost += manhattan(x, y, OX, OY);
    return cost;
}

long long routeCostReversedSegment(const vector<int>& seq, int l, int r, const vector<Order>& orders) {
    const int OX = 400, OY = 400;
    long long cost = 0;
    int x = OX, y = OY;
    int m = (int)seq.size();
    for (int i = 0; i < m; ++i) {
        int idx;
        if (i < l || i > r) idx = seq[i];
        else idx = seq[r - (i - l)];
        const Order& o = orders[idx];
        cost += manhattan(x, y, o.a, o.b);
        cost += manhattan(o.a, o.b, o.c, o.d);
        x = o.c; y = o.d;
    }
    cost += manhattan(x, y, OX, OY);
    return cost;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    const int N = 1000;
    vector<Order> all(N);
    for (int i = 0; i < N; ++i) {
        int a, b, c, d;
        if (!(cin >> a >> b >> c >> d)) return 0;
        all[i] = {a, b, c, d, i + 1, 0};
    }
    const int OX = 400, OY = 400;

    // Compute single loop cost (office -> pickup -> delivery -> office)
    for (int i = 0; i < N; ++i) {
        long long L = 0;
        L += manhattan(OX, OY, all[i].a, all[i].b);
        L += manhattan(all[i].a, all[i].b, all[i].c, all[i].d);
        L += manhattan(all[i].c, all[i].d, OX, OY);
        all[i].loopCost = L;
    }

    // Select 50 orders with smallest loop cost
    vector<int> idxs(N);
    iota(idxs.begin(), idxs.end(), 0);
    nth_element(idxs.begin(), idxs.begin() + 50, idxs.end(), [&](int i, int j){
        if (all[i].loopCost != all[j].loopCost) return all[i].loopCost < all[j].loopCost;
        // tie-breaker: closer pickup to office
        int di = manhattan(OX, OY, all[i].a, all[i].b);
        int dj = manhattan(OX, OY, all[j].a, all[j].b);
        return di < dj;
    });
    idxs.resize(50);

    // Build greedy initial sequence: nearest neighbor in terms of D->P connection
    vector<int> used(50, 0);
    vector<int> seq;
    seq.reserve(50);

    // Map local indices to original indices for convenience
    vector<Order> sel(50);
    for (int i = 0; i < 50; ++i) sel[i] = all[idxs[i]];

    // Choose start: pickup closest to office
    int start = -1;
    int bestd = INT_MAX;
    for (int i = 0; i < 50; ++i) {
        int d = manhattan(OX, OY, sel[i].a, sel[i].b);
        if (d < bestd) {
            bestd = d;
            start = i;
        }
    }
    seq.push_back(start);
    used[start] = 1;
    int cx = sel[start].c, cy = sel[start].d;

    for (int k = 1; k < 50; ++k) {
        int nxt = -1; int bd = INT_MAX; long long tie = LLONG_MAX;
        for (int i = 0; i < 50; ++i) if (!used[i]) {
            int d = manhattan(cx, cy, sel[i].a, sel[i].b);
            long long tiebreak = sel[i].loopCost;
            if (d < bd || (d == bd && tiebreak < tie)) {
                bd = d; tie = tiebreak; nxt = i;
            }
        }
        seq.push_back(nxt);
        used[nxt] = 1;
        cx = sel[nxt].c; cy = sel[nxt].d;
    }

    // 2-opt on the sequence (reversals)
    long long bestCost = routeCost(seq, sel);
    bool improved = true;
    while (improved) {
        improved = false;
        for (int l = 0; l < 50; ++l) {
            for (int r = l + 1; r < 50; ++r) {
                long long newCost = routeCostReversedSegment(seq, l, r, sel);
                if (newCost < bestCost) {
                    reverse(seq.begin() + l, seq.begin() + r + 1);
                    bestCost = newCost;
                    improved = true;
                    goto next_iteration;
                }
            }
        }
        next_iteration:;
    }

    // Output in the visiting order
    cout << 50;
    for (int i = 0; i < 50; ++i) {
        cout << ' ' << sel[seq[i]].id;
    }
    cout << '\n';

    // Build route: start at (400,400), then for each order: pickup -> delivery, then return to (400,400)
    vector<pair<int,int>> path;
    path.reserve(1 + 2*50 + 1);
    path.emplace_back(OX, OY);
    for (int i = 0; i < 50; ++i) {
        const Order& o = sel[seq[i]];
        path.emplace_back(o.a, o.b);
        path.emplace_back(o.c, o.d);
    }
    path.emplace_back(OX, OY);

    cout << path.size();
    for (auto &p : path) {
        cout << ' ' << p.first << ' ' << p.second;
    }
    cout << '\n';

    return 0;
}