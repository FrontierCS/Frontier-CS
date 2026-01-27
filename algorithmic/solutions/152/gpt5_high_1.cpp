#include <bits/stdc++.h>
using namespace std;

struct Order {
    int a, b, c, d;
    int idx; // 1-based
};

inline int manhattan(int x1, int y1, int x2, int y2) {
    return abs(x1 - x2) + abs(y1 - y2);
}

long long compute_total_cost(const vector<int>& seq, const vector<Order>& orders, int xc=400, int yc=400) {
    if (seq.empty()) return 0;
    long long cost = 0;
    const Order& first = orders[seq[0]];
    cost += manhattan(xc, yc, first.a, first.b);
    for (size_t i = 0; i < seq.size(); ++i) {
        const Order& cur = orders[seq[i]];
        cost += manhattan(cur.a, cur.b, cur.c, cur.d);
        if (i + 1 < seq.size()) {
            const Order& nxt = orders[seq[i+1]];
            cost += manhattan(cur.c, cur.d, nxt.a, nxt.b);
        }
    }
    const Order& last = orders[seq.back()];
    cost += manhattan(last.c, last.d, xc, yc);
    return cost;
}

void two_opt(vector<int>& seq, const vector<Order>& orders) {
    long long best_cost = compute_total_cost(seq, orders);
    bool improved = true;
    int n = (int)seq.size();
    while (improved) {
        improved = false;
        for (int l = 0; l < n - 1; ++l) {
            for (int r = l + 1; r < n; ++r) {
                vector<int> tmp = seq;
                reverse(tmp.begin() + l, tmp.begin() + r + 1);
                long long new_cost = compute_total_cost(tmp, orders);
                if (new_cost < best_cost) {
                    seq.swap(tmp);
                    best_cost = new_cost;
                    improved = true;
                    goto next_iter;
                }
            }
        }
        next_iter:;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 1000;
    vector<Order> orders(N);
    for (int i = 0; i < N; ++i) {
        int a, b, c, d;
        if (!(cin >> a >> b >> c >> d)) return 0;
        orders[i] = {a, b, c, d, i + 1};
    }

    const int XC = 400, YC = 400;
    const int M = 50;

    vector<int> seq; seq.reserve(M);
    vector<char> used(N, 0);

    int curx = XC, cury = YC;
    double lambda = 0.3; // weight for returning-to-center heuristic

    for (int k = 0; k < M; ++k) {
        int best_idx = -1;
        double best_score = 1e100;
        for (int i = 0; i < N; ++i) {
            if (used[i]) continue;
            const Order& o = orders[i];
            int d1 = manhattan(curx, cury, o.a, o.b);
            int d2 = manhattan(o.a, o.b, o.c, o.d);
            int d3 = manhattan(o.c, o.d, XC, YC);
            double score = d1 + d2 + lambda * d3;
            if (score < best_score) {
                best_score = score;
                best_idx = i;
            }
        }
        if (best_idx == -1) break; // Should not happen
        used[best_idx] = 1;
        seq.push_back(best_idx);
        curx = orders[best_idx].c;
        cury = orders[best_idx].d;
    }

    // In case something went wrong and we selected less than M (shouldn't happen), fill with smallest individual costs
    if ((int)seq.size() < M) {
        vector<pair<long long, int>> cand;
        for (int i = 0; i < N; ++i) if (!used[i]) {
            const Order& o = orders[i];
            long long cost_alone = manhattan(XC, YC, o.a, o.b) + manhattan(o.a, o.b, o.c, o.d) + manhattan(o.c, o.d, XC, YC);
            cand.emplace_back(cost_alone, i);
        }
        sort(cand.begin(), cand.end());
        for (size_t i = 0; i < cand.size() && (int)seq.size() < M; ++i) {
            seq.push_back(cand[i].second);
            used[cand[i].second] = 1;
        }
    }

    // Improve order with 2-opt
    two_opt(seq, orders);

    // Output
    // m and selected indices (1-based). We'll output in the final route order.
    cout << M;
    for (int i = 0; i < M; ++i) {
        cout << ' ' << orders[seq[i]].idx;
    }
    cout << '\n';

    // Build route points: start, then for each order: pickup, drop, finally back to start
    vector<pair<int,int>> route;
    route.emplace_back(XC, YC);
    for (int i = 0; i < M; ++i) {
        const Order& o = orders[seq[i]];
        route.emplace_back(o.a, o.b);
        route.emplace_back(o.c, o.d);
    }
    route.emplace_back(XC, YC);

    cout << route.size();
    for (auto &p : route) {
        cout << ' ' << p.first << ' ' << p.second;
    }
    cout << '\n';

    return 0;
}