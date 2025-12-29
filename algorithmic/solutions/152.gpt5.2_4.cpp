#include <bits/stdc++.h>
using namespace std;

struct Order {
    int a, b, c, d;
};

static inline int manhattan(int x1, int y1, int x2, int y2) {
    return abs(x1 - x2) + abs(y1 - y2);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 1000;
    vector<Order> ord(N);
    for (int i = 0; i < N; i++) {
        cin >> ord[i].a >> ord[i].b >> ord[i].c >> ord[i].d;
    }

    const int OX = 400, OY = 400;

    vector<pair<long long,int>> score;
    score.reserve(N);
    for (int i = 0; i < N; i++) {
        long long s = 0;
        s += manhattan(OX, OY, ord[i].a, ord[i].b);
        s += manhattan(ord[i].a, ord[i].b, ord[i].c, ord[i].d);
        s += manhattan(ord[i].c, ord[i].d, OX, OY);
        score.push_back({s, i});
    }
    sort(score.begin(), score.end());

    const int M = 50;
    vector<int> picked;
    picked.reserve(M);
    for (int i = 0; i < M; i++) picked.push_back(score[i].second);

    // Build route: office -> pickups (NN) -> deliveries (NN) -> office
    vector<pair<int,int>> route;
    route.reserve(1 + M + M + 1);
    route.push_back({OX, OY});

    // Nearest neighbor for pickups
    vector<char> usedP(M, 0);
    int cx = OX, cy = OY;
    for (int step = 0; step < M; step++) {
        int bestj = -1;
        int bestd = INT_MAX;
        for (int j = 0; j < M; j++) if (!usedP[j]) {
            const auto &o = ord[picked[j]];
            int d = manhattan(cx, cy, o.a, o.b);
            if (d < bestd) {
                bestd = d;
                bestj = j;
            }
        }
        usedP[bestj] = 1;
        const auto &o = ord[picked[bestj]];
        route.push_back({o.a, o.b});
        cx = o.a; cy = o.b;
    }

    // Nearest neighbor for deliveries
    vector<char> usedD(M, 0);
    for (int step = 0; step < M; step++) {
        int bestj = -1;
        int bestd = INT_MAX;
        for (int j = 0; j < M; j++) if (!usedD[j]) {
            const auto &o = ord[picked[j]];
            int d = manhattan(cx, cy, o.c, o.d);
            if (d < bestd) {
                bestd = d;
                bestj = j;
            }
        }
        usedD[bestj] = 1;
        const auto &o = ord[picked[bestj]];
        route.push_back({o.c, o.d});
        cx = o.c; cy = o.d;
    }

    route.push_back({OX, OY});

    // Output
    cout << M;
    for (int i = 0; i < M; i++) cout << ' ' << (picked[i] + 1);
    cout << "\n";

    cout << route.size();
    for (auto &p : route) cout << ' ' << p.first << ' ' << p.second;
    cout << "\n";

    return 0;
}