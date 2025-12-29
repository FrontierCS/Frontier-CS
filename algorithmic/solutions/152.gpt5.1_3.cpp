#include <bits/stdc++.h>
using namespace std;

struct Order {
    int a, b, c, d;
    int idx;
    long long baseCost;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 1000;
    vector<Order> ords;
    ords.reserve(N);

    int a, b, c, d;
    for (int i = 0; i < N; i++) {
        if (!(cin >> a >> b >> c >> d)) {
            // If input is shorter than expected, output a trivial answer.
            if (i == 0) {
                cout << 0 << "\n";
                cout << 2 << " " << 400 << " " << 400 << " " << 400 << " " << 400 << "\n";
            }
            return 0;
        }
        Order o;
        o.a = a; o.b = b; o.c = c; o.d = d; o.idx = i;
        int ox = 400, oy = 400;
        long long base = 0;
        base += abs(ox - a) + abs(oy - b);
        base += abs(a - c) + abs(b - d);
        base += abs(c - ox) + abs(d - oy);
        o.baseCost = base;
        ords.push_back(o);
    }

    if (ords.empty()) {
        cout << 0 << "\n";
        cout << 2 << " " << 400 << " " << 400 << " " << 400 << " " << 400 << "\n";
        return 0;
    }

    sort(ords.begin(), ords.end(), [](const Order &x, const Order &y) {
        if (x.baseCost != y.baseCost) return x.baseCost < y.baseCost;
        return x.idx < y.idx;
    });

    int m = 50;
    if ((int)ords.size() < m) m = (int)ords.size();
    vector<Order> chosen(ords.begin(), ords.begin() + m);

    vector<int> pickupOrder;
    vector<int> deliveryOrder;
    pickupOrder.reserve(m);
    deliveryOrder.reserve(m);
    vector<char> usedPick(m, false), usedDel(m, false);

    int curx = 400, cury = 400;
    // Nearest-neighbor for pickups
    for (int it = 0; it < m; ++it) {
        int best = -1;
        int bestDist = INT_MAX;
        for (int k = 0; k < m; k++) {
            if (usedPick[k]) continue;
            int dist = abs(curx - chosen[k].a) + abs(cury - chosen[k].b);
            if (dist < bestDist) {
                bestDist = dist;
                best = k;
            }
        }
        if (best == -1) break;
        usedPick[best] = true;
        pickupOrder.push_back(best);
        curx = chosen[best].a;
        cury = chosen[best].b;
    }

    // Nearest-neighbor for deliveries starting from last pickup
    fill(usedDel.begin(), usedDel.end(), false);
    for (int it = 0; it < m; ++it) {
        int best = -1;
        int bestDist = INT_MAX;
        for (int k = 0; k < m; k++) {
            if (usedDel[k]) continue;
            int dist = abs(curx - chosen[k].c) + abs(cury - chosen[k].d);
            if (dist < bestDist) {
                bestDist = dist;
                best = k;
            }
        }
        if (best == -1) break;
        usedDel[best] = true;
        deliveryOrder.push_back(best);
        curx = chosen[best].c;
        cury = chosen[best].d;
    }

    vector<pair<int,int>> route;
    route.reserve(2 + pickupOrder.size() + deliveryOrder.size());
    route.emplace_back(400, 400);
    for (int idxInChosen : pickupOrder) {
        route.emplace_back(chosen[idxInChosen].a, chosen[idxInChosen].b);
    }
    for (int idxInChosen : deliveryOrder) {
        route.emplace_back(chosen[idxInChosen].c, chosen[idxInChosen].d);
    }
    route.emplace_back(400, 400);

    cout << m;
    for (int i = 0; i < m; i++) {
        cout << " " << (chosen[i].idx + 1);
    }
    cout << "\n";

    int n = (int)route.size();
    cout << n;
    for (auto &p : route) {
        cout << " " << p.first << " " << p.second;
    }
    cout << "\n";

    return 0;
}