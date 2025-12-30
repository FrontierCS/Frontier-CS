#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 1000;
    const int OFFICE_X = 400;
    const int OFFICE_Y = 400;

    auto manhattan = [](int x1, int y1, int x2, int y2) -> int {
        return abs(x1 - x2) + abs(y1 - y2);
    };

    struct Order {
        int id;
        int ax, ay, cx, cy;
        long long base;
    };

    vector<Order> orders(N);
    for (int i = 0; i < N; i++) {
        int a, b, c, d;
        if (!(cin >> a >> b >> c >> d)) return 0;
        orders[i].id = i + 1;
        orders[i].ax = a;
        orders[i].ay = b;
        orders[i].cx = c;
        orders[i].cy = d;
        long long base = 0;
        base += manhattan(OFFICE_X, OFFICE_Y, a, b);
        base += manhattan(a, b, c, d);
        base += manhattan(c, d, OFFICE_X, OFFICE_Y);
        orders[i].base = base;
    }

    sort(orders.begin(), orders.end(),
         [](const Order& p, const Order& q) { return p.base < q.base; });

    const int M = 50;
    vector<Order> sel(orders.begin(), orders.begin() + M);

    // Initial sequence: greedy nearest neighbor based on (cur -> restaurant) + (restaurant -> dest)
    vector<int> seq(M);
    vector<char> used(M, false);
    int curx = OFFICE_X, cury = OFFICE_Y;
    for (int step = 0; step < M; step++) {
        int best = -1;
        long long bestCost = (1LL << 60);
        for (int j = 0; j < M; j++) if (!used[j]) {
            long long cost = manhattan(curx, cury, sel[j].ax, sel[j].ay)
                           + manhattan(sel[j].ax, sel[j].ay, sel[j].cx, sel[j].cy);
            if (cost < bestCost) {
                bestCost = cost;
                best = j;
            }
        }
        used[best] = true;
        seq[step] = best;
        curx = sel[best].cx;
        cury = sel[best].cy;
    }

    auto crossCost = [&](const vector<int>& s) -> long long {
        if (s.empty()) return 0;
        long long cost = 0;
        cost += manhattan(OFFICE_X, OFFICE_Y, sel[s[0]].ax, sel[s[0]].ay);
        for (int i = 0; i + 1 < (int)s.size(); i++) {
            const auto& o1 = sel[s[i]];
            const auto& o2 = sel[s[i + 1]];
            cost += manhattan(o1.cx, o1.cy, o2.ax, o2.ay);
        }
        const auto& last = sel[s.back()];
        cost += manhattan(last.cx, last.cy, OFFICE_X, OFFICE_Y);
        return cost;
    };

    // 2-opt local search on order sequence
    long long bestCost = crossCost(seq);
    bool improved = true;
    while (improved) {
        improved = false;
        for (int l = 0; l < M; l++) {
            for (int r = l + 1; r < M; r++) {
                vector<int> tmp = seq;
                reverse(tmp.begin() + l, tmp.begin() + r + 1);
                long long c = crossCost(tmp);
                if (c < bestCost) {
                    seq.swap(tmp);
                    bestCost = c;
                    improved = true;
                    goto NEXT_ITER;
                }
            }
        }
    NEXT_ITER:
        ;
    }

    // Build final path: office -> (Ri->Di for each in seq) -> office
    vector<pair<int,int>> path;
    path.reserve(2 * M + 2);
    path.emplace_back(OFFICE_X, OFFICE_Y);
    for (int idx : seq) {
        path.emplace_back(sel[idx].ax, sel[idx].ay);
        path.emplace_back(sel[idx].cx, sel[idx].cy);
    }
    if (path.back().first != OFFICE_X || path.back().second != OFFICE_Y) {
        path.emplace_back(OFFICE_X, OFFICE_Y);
    }

    // Output
    cout << M;
    for (int i = 0; i < M; i++) {
        cout << ' ' << sel[seq[i]].id;
    }
    cout << '\n';

    int n = (int)path.size();
    cout << n;
    for (int i = 0; i < n; i++) {
        cout << ' ' << path[i].first << ' ' << path[i].second;
    }
    cout << '\n';

    return 0;
}