#include <bits/stdc++.h>
using namespace std;

struct Order {
    int idx;
    int a, b, c, d;
    int cost;
};

inline int manhattan(int x1, int y1, int x2, int y2) {
    return abs(x1 - x2) + abs(y1 - y2);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    const int N = 1000;
    const int CENTER_X = 400, CENTER_Y = 400;
    vector<Order> orders;
    orders.reserve(N);
    for (int i = 0; i < N; ++i) {
        int a, b, c, d;
        if (!(cin >> a >> b >> c >> d)) return 0;
        Order o;
        o.idx = i + 1;
        o.a = a; o.b = b; o.c = c; o.d = d;
        o.cost = manhattan(CENTER_X, CENTER_Y, a, b)
               + manhattan(a, b, c, d)
               + manhattan(c, d, CENTER_X, CENTER_Y);
        orders.push_back(o);
    }
    
    // Select 50 orders with smallest simple cost
    nth_element(orders.begin(), orders.begin() + 50, orders.end(), [](const Order& x, const Order& y){
        return x.cost < y.cost;
    });
    vector<Order> chosen(orders.begin(), orders.begin() + 50);
    // For stable behavior, sort chosen by cost then index
    sort(chosen.begin(), chosen.end(), [](const Order& x, const Order& y){
        if (x.cost != y.cost) return x.cost < y.cost;
        return x.idx < y.idx;
    });
    
    // Build route greedily allowing interleaving: at each step go to nearest candidate (pickup or eligible drop)
    int M = (int)chosen.size(); // should be 50
    vector<bool> picked(M, false), delivered(M, false);
    int remaining_picks = M, remaining_delivs = M;
    
    vector<pair<int,int>> route;
    route.emplace_back(CENTER_X, CENTER_Y);
    int curx = CENTER_X, cury = CENTER_Y;
    
    while (remaining_delivs > 0) {
        int bestIdx = -1;
        bool bestIsPickup = true;
        int bestDist = INT_MAX;
        // Consider pickups
        for (int i = 0; i < M; ++i) {
            if (!picked[i]) {
                int d = manhattan(curx, cury, chosen[i].a, chosen[i].b);
                if (d < bestDist) {
                    bestDist = d;
                    bestIdx = i;
                    bestIsPickup = true;
                }
            }
        }
        // Consider deliveries of already picked and not yet delivered
        for (int i = 0; i < M; ++i) {
            if (picked[i] && !delivered[i]) {
                int d = manhattan(curx, cury, chosen[i].c, chosen[i].d);
                if (d < bestDist) {
                    bestDist = d;
                    bestIdx = i;
                    bestIsPickup = false;
                }
            }
        }
        if (bestIdx == -1) break; // should not happen
        if (bestIsPickup) {
            curx = chosen[bestIdx].a;
            cury = chosen[bestIdx].b;
            picked[bestIdx] = true;
            --remaining_picks;
        } else {
            curx = chosen[bestIdx].c;
            cury = chosen[bestIdx].d;
            delivered[bestIdx] = true;
            --remaining_delivs;
        }
        route.emplace_back(curx, cury);
    }
    // Return to center
    if (route.back().first != CENTER_X || route.back().second != CENTER_Y) {
        route.emplace_back(CENTER_X, CENTER_Y);
    }
    
    // Output
    cout << M;
    for (int i = 0; i < M; ++i) cout << ' ' << chosen[i].idx;
    cout << '\n';
    cout << (int)route.size();
    for (auto &p : route) {
        cout << ' ' << p.first << ' ' << p.second;
    }
    cout << '\n';
    return 0;
}