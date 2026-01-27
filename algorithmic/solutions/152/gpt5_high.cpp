#include <bits/stdc++.h>
using namespace std;

struct Order {
    int a, b, c, d;
};

inline int manhattan(int x1, int y1, int x2, int y2) {
    return abs(x1 - x2) + abs(y1 - y2);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 1000;
    const int BASEX = 400, BASEY = 400;

    vector<Order> orders(N);
    for (int i = 0; i < N; i++) {
        int a, b, c, d;
        if (!(cin >> a >> b >> c >> d)) return 0;
        orders[i] = {a, b, c, d};
    }

    // Score each order by base -> pickup -> delivery -> base cost
    vector<pair<int, int>> score_idx; // (score, index)
    score_idx.reserve(N);
    for (int i = 0; i < N; i++) {
        const auto &o = orders[i];
        int s = manhattan(BASEX, BASEY, o.a, o.b)
              + manhattan(o.a, o.b, o.c, o.d)
              + manhattan(o.c, o.d, BASEX, BASEY);
        score_idx.emplace_back(s, i);
    }
    sort(score_idx.begin(), score_idx.end());

    // Choose 50 orders with smallest individual round-trip cost
    const int M = 50;
    vector<int> chosen_indices;
    chosen_indices.reserve(M);
    vector<char> chosen(N, 0);
    for (int i = 0; i < M; i++) {
        int idx = score_idx[i].second;
        chosen_indices.push_back(idx);
        chosen[idx] = 1;
    }

    // Precedence-aware greedy route construction over selected orders
    vector<char> picked(N, 0), delivered(N, 0);
    int delivered_count = 0;

    vector<pair<int,int>> route;
    route.emplace_back(BASEX, BASEY);

    auto markAtCurrent = [&](int x, int y) {
        // Mark all pickups at current position
        for (int id : chosen_indices) {
            if (!picked[id]) {
                if (orders[id].a == x && orders[id].b == y) {
                    picked[id] = 1;
                }
            }
        }
        // Mark all deliveries at current position whose pickups are already done
        for (int id : chosen_indices) {
            if (picked[id] && !delivered[id]) {
                if (orders[id].c == x && orders[id].d == y) {
                    delivered[id] = 1;
                    delivered_count++;
                }
            }
        }
    };

    // Initial mark at base (for any pickups located at base)
    markAtCurrent(BASEX, BASEY);

    int curx = BASEX, cury = BASEY;
    while (delivered_count < M) {
        int best_id = -1;
        bool best_is_delivery = false;
        int best_dist = INT_MAX;

        for (int id : chosen_indices) {
            if (!picked[id]) {
                int d = manhattan(curx, cury, orders[id].a, orders[id].b);
                if (d < best_dist || (d == best_dist && !best_is_delivery)) {
                    best_dist = d;
                    best_id = id;
                    best_is_delivery = false;
                }
            } else if (!delivered[id]) {
                int d = manhattan(curx, cury, orders[id].c, orders[id].d);
                // Prefer deliveries on tie to reduce carrying items
                if (d < best_dist || (d == best_dist && best_is_delivery == false)) {
                    best_dist = d;
                    best_id = id;
                    best_is_delivery = true;
                }
            }
        }

        if (best_id == -1) {
            // Should not happen, but fallback to base to avoid infinite loop
            route.emplace_back(BASEX, BASEY);
            curx = BASEX; cury = BASEY;
            markAtCurrent(curx, cury);
            continue;
        }

        int nx = best_is_delivery ? orders[best_id].c : orders[best_id].a;
        int ny = best_is_delivery ? orders[best_id].d : orders[best_id].b;

        // Append next point even if equal to current to create a new time index
        route.emplace_back(nx, ny);
        curx = nx; cury = ny;
        markAtCurrent(curx, cury);
    }

    // Return to base
    if (!(curx == BASEX && cury == BASEY)) {
        route.emplace_back(BASEX, BASEY);
        curx = BASEX; cury = BASEY;
        markAtCurrent(curx, cury);
    } else {
        // Ensure the last index equals base distinct from the first (s<t possibility for base deliveries)
        // Append duplicate base to be safe
        route.emplace_back(BASEX, BASEY);
        markAtCurrent(curx, cury);
    }

    // Output
    cout << M;
    for (int id : chosen_indices) cout << ' ' << (id + 1);
    cout << '\n';

    cout << (int)route.size();
    for (auto &p : route) cout << ' ' << p.first << ' ' << p.second;
    cout << '\n';

    return 0;
}