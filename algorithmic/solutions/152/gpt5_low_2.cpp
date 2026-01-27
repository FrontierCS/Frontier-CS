#include <bits/stdc++.h>
using namespace std;

struct Order {
    int a, b, c, d;
    long long score;
    int idx;
};

long long manhattan(int x1, int y1, int x2, int y2) {
    return llabs(x1 - x2) + llabs(y1 - y2);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 1000;
    const int M = 50;
    const int CX = 400, CY = 400;

    vector<Order> orders(N);
    for (int i = 0; i < N; i++) {
        int a, b, c, d;
        if (!(cin >> a >> b >> c >> d)) {
            return 0;
        }
        orders[i] = {a, b, c, d, 0, i};
        long long s = 0;
        s += manhattan(CX, CY, a, b);
        s += manhattan(a, b, c, d);
        s += manhattan(c, d, CX, CY);
        orders[i].score = s;
        orders[i].idx = i;
    }

    // Select 50 orders with minimal estimated score
    vector<Order> sel = orders;
    nth_element(sel.begin(), sel.begin() + M, sel.end(), [](const Order& x, const Order& y){
        if (x.score != y.score) return x.score < y.score;
        return x.idx < y.idx;
    });
    sel.resize(M);

    // Prepare points for pickups and deliveries
    vector<pair<int,int>> pickups(M), deliveries(M);
    vector<int> ids(M);
    for (int i = 0; i < M; i++) {
        pickups[i] = {sel[i].a, sel[i].b};
        deliveries[i] = {sel[i].c, sel[i].d};
        ids[i] = sel[i].idx + 1; // 1-based
    }

    // Build route: start at center
    vector<pair<int,int>> path;
    path.emplace_back(CX, CY);

    // Visit all pickups by nearest neighbor
    vector<char> picked(M, 0);
    int curx = CX, cury = CY;
    for (int cnt = 0; cnt < M; cnt++) {
        int best = -1;
        long long bestd = (1LL<<60);
        for (int i = 0; i < M; i++) if (!picked[i]) {
            long long d = manhattan(curx, cury, pickups[i].first, pickups[i].second);
            if (d < bestd) {
                bestd = d;
                best = i;
            }
        }
        if (best != -1) {
            curx = pickups[best].first;
            cury = pickups[best].second;
            path.emplace_back(curx, cury);
            picked[best] = 1;
        }
    }

    // Deliver all by nearest neighbor
    vector<char> delivered(M, 0);
    for (int cnt = 0; cnt < M; cnt++) {
        int best = -1;
        long long bestd = (1LL<<60);
        for (int i = 0; i < M; i++) if (!delivered[i]) {
            long long d = manhattan(curx, cury, deliveries[i].first, deliveries[i].second);
            if (d < bestd) {
                bestd = d;
                best = i;
            }
        }
        if (best != -1) {
            curx = deliveries[best].first;
            cury = deliveries[best].second;
            path.emplace_back(curx, cury);
            delivered[best] = 1;
        }
    }

    // Return to center
    if (curx != CX || cury != CY) {
        path.emplace_back(CX, CY);
    } else {
        // Ensure both start and end are (400,400); already true since last is center
    }

    // Output
    cout << M;
    for (int i = 0; i < M; i++) cout << " " << ids[i];
    cout << "\n";

    cout << path.size();
    for (auto &p : path) cout << " " << p.first << " " << p.second;
    cout << "\n";

    return 0;
}