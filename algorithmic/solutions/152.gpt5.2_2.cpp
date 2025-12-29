#include <bits/stdc++.h>
using namespace std;

struct Order {
    int id;
    int a, b, c, d;
};

static inline int manhattan(int x1, int y1, int x2, int y2) {
    return abs(x1 - x2) + abs(y1 - y2);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<Order> orders(1000);
    for (int i = 0; i < 1000; i++) {
        orders[i].id = i + 1;
        cin >> orders[i].a >> orders[i].b >> orders[i].c >> orders[i].d;
        if (!cin) return 0;
    }

    const int CX = 400, CY = 400;

    vector<pair<long long,int>> scored;
    scored.reserve(1000);
    for (int i = 0; i < 1000; i++) {
        auto &o = orders[i];
        long long s = 0;
        s += manhattan(CX, CY, o.a, o.b);
        s += manhattan(o.a, o.b, o.c, o.d);
        s += manhattan(o.c, o.d, CX, CY);
        scored.emplace_back(s, i);
    }
    sort(scored.begin(), scored.end());

    vector<Order> cand;
    cand.reserve(50);
    for (int k = 0; k < 50; k++) cand.push_back(orders[scored[k].second]);

    // Greedy order by nearest pickup from current position (deliver immediately).
    vector<Order> seq;
    seq.reserve(50);
    vector<char> used(50, 0);
    int curx = CX, cury = CY;
    for (int step = 0; step < 50; step++) {
        int best = -1;
        long long bestScore = (1LL<<60);
        for (int i = 0; i < 50; i++) if (!used[i]) {
            auto &o = cand[i];
            long long s = 0;
            s += manhattan(curx, cury, o.a, o.b);
            s += manhattan(o.a, o.b, o.c, o.d);
            // small lookahead: prefer deliveries closer to center for future
            s += manhattan(o.c, o.d, CX, CY) / 10;
            if (s < bestScore) {
                bestScore = s;
                best = i;
            }
        }
        used[best] = 1;
        seq.push_back(cand[best]);
        curx = cand[best].c;
        cury = cand[best].d;
    }

    // Build route: center -> (pickup,delivery)* -> center
    vector<pair<int,int>> route;
    route.reserve(2 * 50 + 2);
    route.push_back({CX, CY});
    for (auto &o : seq) {
        route.push_back({o.a, o.b});
        route.push_back({o.c, o.d});
    }
    route.push_back({CX, CY});

    // Output
    cout << 50;
    for (auto &o : seq) cout << ' ' << o.id;
    cout << "\n";

    cout << route.size();
    for (auto &p : route) cout << ' ' << p.first << ' ' << p.second;
    cout << "\n";

    return 0;
}