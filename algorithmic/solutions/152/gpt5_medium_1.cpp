#include <bits/stdc++.h>
using namespace std;

struct Order {
    int a, b, c, d;
    long long score;
    int idx;
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

    vector<Order> orders(N);
    for (int i = 0; i < N; ++i) {
        int a, b, c, d;
        if (!(cin >> a >> b >> c >> d)) return 0;
        orders[i].a = a; orders[i].b = b; orders[i].c = c; orders[i].d = d;
        orders[i].idx = i;
        long long s = (long long)manhattan(a, b, OX, OY) + (long long)manhattan(c, d, OX, OY);
        orders[i].score = s;
    }

    // Choose M orders with smallest score (close to center)
    vector<int> cand_idx(N);
    iota(cand_idx.begin(), cand_idx.end(), 0);
    sort(cand_idx.begin(), cand_idx.end(), [&](int i, int j){
        if (orders[i].score != orders[j].score) return orders[i].score < orders[j].score;
        return orders[i].idx < orders[j].idx;
    });
    vector<int> chosen;
    chosen.reserve(M);
    for (int i = 0; i < M; ++i) chosen.push_back(cand_idx[i]);

    // Prepare for routing
    // Greedy nearest neighbor: first all pickups, then all deliveries
    vector<int> pickOrder;
    vector<int> delOrder;
    pickOrder.reserve(M);
    delOrder.reserve(M);

    vector<char> usedPick(M, false);
    vector<char> usedDel(M, false);

    // Build arrays for easy access
    vector<int> ax(M), ay(M), cx(M), cy(M), origIdx(M);
    for (int i = 0; i < M; ++i) {
        auto &o = orders[chosen[i]];
        ax[i] = o.a; ay[i] = o.b; cx[i] = o.c; cy[i] = o.d; origIdx[i] = o.idx;
    }

    int curx = OX, cury = OY;
    for (int step = 0; step < M; ++step) {
        int best = -1, bestd = INT_MAX;
        for (int i = 0; i < M; ++i) {
            if (usedPick[i]) continue;
            int d = manhattan(curx, cury, ax[i], ay[i]);
            if (d < bestd) {
                bestd = d; best = i;
            }
        }
        usedPick[best] = true;
        pickOrder.push_back(best);
        curx = ax[best]; cury = ay[best];
    }

    // Deliveries
    for (int step = 0; step < M; ++step) {
        int best = -1, bestd = INT_MAX;
        for (int i = 0; i < M; ++i) {
            if (usedDel[i]) continue;
            int d = manhattan(curx, cury, cx[i], cy[i]);
            if (d < bestd) {
                bestd = d; best = i;
            }
        }
        usedDel[best] = true;
        delOrder.push_back(best);
        curx = cx[best]; cury = cy[best];
    }

    // Build route: start O, all pickups, all deliveries, end O
    vector<pair<int,int>> route;
    route.reserve(2*M + 2);
    route.emplace_back(OX, OY);
    for (int id : pickOrder) route.emplace_back(ax[id], ay[id]);
    for (int id : delOrder) route.emplace_back(cx[id], cy[id]);
    route.emplace_back(OX, OY);

    // Output
    cout << M;
    for (int i = 0; i < M; ++i) {
        cout << ' ' << (origIdx[i] + 1);
    }
    cout << '\n';
    cout << route.size();
    for (auto &p : route) {
        cout << ' ' << p.first << ' ' << p.second;
    }
    cout << '\n';

    return 0;
}