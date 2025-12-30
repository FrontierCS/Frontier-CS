#include <bits/stdc++.h>
using namespace std;

struct Order {
    int idx;
    int ax, ay, cx, cy;
    int L;
    int Score;
};

inline int manh(int x1, int y1, int x2, int y2) {
    return abs(x1 - x2) + abs(y1 - y2);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int OX = 400, OY = 400;
    vector<Order> orders;
    orders.reserve(1000);
    for (int i = 1; i <= 1000; i++) {
        int a, b, c, d;
        if (!(cin >> a >> b >> c >> d)) break;
        Order o;
        o.idx = i;
        o.ax = a; o.ay = b; o.cx = c; o.cy = d;
        o.L = manh(a, b, c, d);
        o.Score = manh(OX, OY, a, b) + o.L + manh(c, d, OX, OY);
        orders.push_back(o);
    }
    int N = (int)orders.size();
    if (N == 0) {
        // Fallback (should not happen in official judge)
        cout << 50;
        for (int i = 0; i < 50; i++) cout << " " << 1;
        cout << "\n";
        cout << 2 << " " << OX << " " << OY << " " << OX << " " << OY << "\n";
        return 0;
    }

    // Select candidates by smallest individual 400->a->c->400 route length
    sort(orders.begin(), orders.end(), [](const Order& x, const Order& y){
        return x.Score < y.Score;
    });

    int K = min(300, N); // candidate pool size
    vector<int> cand_idx; cand_idx.reserve(K);
    for (int i = 0; i < K; i++) cand_idx.push_back(i);

    // Greedy selection of 50 orders from candidates based on nearest a from current pos
    const int M = 50;
    vector<int> selected_original_indices; selected_original_indices.reserve(M);
    vector<char> used(K, 0);
    int curx = OX, cury = OY;
    for (int t = 0; t < M; t++) {
        int bestj = -1;
        int bestCost = INT_MAX;
        for (int j = 0; j < K; j++) {
            if (used[j]) continue;
            const Order &o = orders[cand_idx[j]];
            int cost = manh(curx, cury, o.ax, o.ay);
            if (cost < bestCost) {
                bestCost = cost;
                bestj = j;
            }
        }
        if (bestj == -1) {
            // Shouldn't happen, but fallback
            for (int j = 0; j < K; j++) if (!used[j]) { bestj = j; break; }
        }
        used[bestj] = 1;
        selected_original_indices.push_back(cand_idx[bestj]); // index into 'orders'
        const Order &o = orders[cand_idx[bestj]];
        curx = o.cx; cury = o.cy;
    }

    // Build arrays for selected orders in the greedy order
    int n = (int)selected_original_indices.size();
    vector<pair<int,int>> A(n), C(n);
    vector<int> sel_idx(n); // index into 'orders'
    for (int i = 0; i < n; i++) {
        sel_idx[i] = selected_original_indices[i];
        const Order &o = orders[sel_idx[i]];
        A[i] = {o.ax, o.ay};
        C[i] = {o.cx, o.cy};
    }

    // Build distance matrix d[u][v] = dist(C[u], A[v])
    vector<vector<int>> d(n, vector<int>(n, 0));
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            d[i][j] = manh(C[i].first, C[i].second, A[j].first, A[j].second);
        }
    }

    auto distOA = [&](int k)->int { return manh(OX, OY, A[k].first, A[k].second); };
    auto distCO = [&](int k)->int { return manh(C[k].first, C[k].second, OX, OY); };

    // Initialize permutation p = 0..n-1 (greedy order)
    vector<int> p(n);
    iota(p.begin(), p.end(), 0);

    // 2-opt on the order sequence with fixed within-order direction (A->C)
    auto connectors_cost = [&](const vector<int>& p)->long long {
        long long cost = 0;
        if (n > 0) {
            cost += distOA(p[0]);
            for (int i = 0; i + 1 < n; i++) cost += d[p[i]][p[i+1]];
            cost += distCO(p[n-1]);
        }
        return cost;
    };

    bool improved = true;
    int iter_guard = 0;
    while (improved && iter_guard < 2000) {
        iter_guard++;
        improved = false;
        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                long long oldLeft, oldRight, newLeft, newRight;
                if (i == 0) oldLeft = distOA(p[i]);
                else oldLeft = d[p[i-1]][p[i]];
                if (j == n - 1) oldRight = distCO(p[j]);
                else oldRight = d[p[j]][p[j+1]];

                if (i == 0) newLeft = distOA(p[j]);
                else newLeft = d[p[i-1]][p[j]];
                if (j == n - 1) newRight = distCO(p[i]);
                else newRight = d[p[i]][p[j+1]];

                long long oldInternal = 0, newInternal = 0;
                for (int k = i; k < j; k++) {
                    oldInternal += d[p[k]][p[k+1]];
                    newInternal += d[p[k+1]][p[k]];
                }

                long long delta = (newLeft + newInternal + newRight) - (oldLeft + oldInternal + oldRight);
                if (delta < 0) {
                    reverse(p.begin() + i, p.begin() + j + 1);
                    improved = true;
                    break;
                }
            }
            if (improved) break;
        }
    }

    // Prepare output:
    // m and r_1..r_m (use the final route order)
    cout << M;
    for (int i = 0; i < n; i++) {
        int ord_index_in_orders = sel_idx[p[i]];
        cout << " " << orders[ord_index_in_orders].idx;
    }
    cout << "\n";

    // Build route: start at office, then a_i, c_i for each in final order, then back to office
    vector<pair<int,int>> route;
    route.reserve(2 * n + 2);
    route.emplace_back(OX, OY);
    for (int i = 0; i < n; i++) {
        int k = p[i];
        route.push_back(A[k]);
        route.push_back(C[k]);
    }
    route.emplace_back(OX, OY);

    cout << route.size();
    for (auto &pt : route) {
        cout << " " << pt.first << " " << pt.second;
    }
    cout << "\n";
    return 0;
}