#include <bits/stdc++.h>
using namespace std;

struct Order {
    int a, b, c, d;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 1000;
    const int OX = 400, OY = 400;

    vector<Order> ord(N);
    for (int i = 0; i < N; i++) {
        if (!(cin >> ord[i].a >> ord[i].b >> ord[i].c >> ord[i].d)) {
            return 0;
        }
    }

    auto dist = [&](int x1, int y1, int x2, int y2) -> int {
        return abs(x1 - x2) + abs(y1 - y2);
    };

    vector<pair<int, int>> cand;
    cand.reserve(N);
    for (int i = 0; i < N; i++) {
        int d = dist(OX, OY, ord[i].a, ord[i].b)
              + dist(ord[i].a, ord[i].b, ord[i].c, ord[i].d)
              + dist(ord[i].c, ord[i].d, OX, OY);
        cand.emplace_back(d, i);
    }

    const int M = 50;
    nth_element(cand.begin(), cand.begin() + M, cand.end());
    vector<int> idxs;
    idxs.reserve(M);
    for (int i = 0; i < M; i++) idxs.push_back(cand[i].second);

    sort(idxs.begin(), idxs.end(), [&](int i, int j) {
        int di = dist(OX, OY, ord[i].a, ord[i].b);
        int dj = dist(OX, OY, ord[j].a, ord[j].b);
        return di < dj;
    });

    vector<pair<int, int>> route;
    route.reserve(2 * M + 2);
    route.emplace_back(OX, OY);
    for (int id : idxs) {
        route.emplace_back(ord[id].a, ord[id].b);
        route.emplace_back(ord[id].c, ord[id].d);
    }
    route.emplace_back(OX, OY);

    cout << M;
    for (int id : idxs) cout << ' ' << (id + 1);
    cout << '\n';

    cout << route.size();
    for (auto &p : route) cout << ' ' << p.first << ' ' << p.second;
    cout << '\n';

    return 0;
}