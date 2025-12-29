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
    vector<Order> ord(N + 1);
    for (int i = 1; i <= N; i++) {
        cin >> ord[i].a >> ord[i].b >> ord[i].c >> ord[i].d;
    }

    const int SX = 400, SY = 400;
    vector<int> chosen;
    chosen.reserve(50);
    vector<char> used(N + 1, 0);

    int curx = SX, cury = SY;
    for (int step = 0; step < 50; step++) {
        int best = -1;
        int bestCost = INT_MAX;

        for (int i = 1; i <= N; i++) if (!used[i]) {
            const auto &o = ord[i];
            int cost = manhattan(curx, cury, o.a, o.b)
                     + manhattan(o.a, o.b, o.c, o.d)
                     + manhattan(o.c, o.d, SX, SY); // small lookahead to end
            if (cost < bestCost) {
                bestCost = cost;
                best = i;
            }
        }

        used[best] = 1;
        chosen.push_back(best);
        curx = ord[best].c;
        cury = ord[best].d;
    }

    vector<pair<int,int>> route;
    route.reserve(102);
    route.push_back({SX, SY});
    for (int idx : chosen) {
        route.push_back({ord[idx].a, ord[idx].b});
        route.push_back({ord[idx].c, ord[idx].d});
    }
    route.push_back({SX, SY});

    cout << 50;
    for (int idx : chosen) cout << ' ' << idx;
    cout << "\n";

    cout << route.size();
    for (auto [x,y] : route) cout << ' ' << x << ' ' << y;
    cout << "\n";

    return 0;
}