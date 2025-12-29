#include <bits/stdc++.h>
using namespace std;

struct Point {
    int x, y;
};

int dist(Point a, Point b) {
    return abs(a.x - b.x) + abs(a.y - b.y);
}

struct Order {
    Point p, d;
    int id;
    int dist_pd;
    int cost;
};

int main() {
    Point o = {400, 400};
    vector<Order> all_orders(1000);
    for (int i = 0; i < 1000; i++) {
        int a, b, c, d;
        cin >> a >> b >> c >> d;
        all_orders[i].p = {a, b};
        all_orders[i].d = {c, d};
        all_orders[i].id = i + 1;
        all_orders[i].dist_pd = dist(all_orders[i].p, all_orders[i].d);
        all_orders[i].cost = dist(o, all_orders[i].p) + all_orders[i].dist_pd + dist(o, all_orders[i].d);
    }
    sort(all_orders.begin(), all_orders.end(), [](const Order& a, const Order& b) {
        return a.cost < b.cost;
    });
    vector<Order> selected(all_orders.begin(), all_orders.begin() + 50);
    int N = 50;
    vector<int> s(N);
    vector<bool> used(N, false);
    int min_start = INT_MAX;
    int first = 0;
    for (int i = 0; i < N; i++) {
        int dc = dist(o, selected[i].p);
        if (dc < min_start) {
            min_start = dc;
            first = i;
        }
    }
    s[0] = first;
    used[first] = true;
    int cur = first;
    for (int pos = 1; pos < N; pos++) {
        int best = -1;
        int min_d = INT_MAX;
        for (int j = 0; j < N; j++) {
            if (!used[j]) {
                int dc = dist(selected[cur].d, selected[j].p);
                if (dc < min_d || (dc == min_d && j < best)) {
                    min_d = dc;
                    best = j;
                }
            }
        }
        s[pos] = best;
        used[best] = true;
        cur = best;
    }
    bool changed = true;
    while (changed) {
        changed = false;
        for (int L = 0; L < N; L++) {
            for (int R = L + 1; R < N; R++) {
                int orig = 0;
                int newc = 0;
                if (L > 0) {
                    int prev = s[L - 1];
                    orig += dist(selected[prev].d, selected[s[L]].p);
                    newc += dist(selected[prev].d, selected[s[R]].p);
                }
                for (int k = L; k < R; k++) {
                    orig += dist(selected[s[k]].d, selected[s[k + 1]].p);
                    newc += dist(selected[s[k + 1]].d, selected[s[k]].p);
                }
                if (R < N - 1) {
                    int nxt = s[R + 1];
                    orig += dist(selected[s[R]].d, selected[nxt].p);
                    newc += dist(selected[s[L]].d, selected[nxt].p);
                }
                if (newc < orig) {
                    reverse(s.begin() + L, s.begin() + R + 1);
                    changed = true;
                }
            }
        }
    }
    vector<int> chosen_ids;
    for (int i = 0; i < N; i++) {
        chosen_ids.push_back(selected[s[i]].id);
    }
    sort(chosen_ids.begin(), chosen_ids.end());
    cout << N;
    for (int id : chosen_ids) cout << " " << id;
    cout << endl;
    vector<Point> route;
    route.push_back(o);
    for (int i = 0; i < N; i++) {
        int idx = s[i];
        route.push_back(selected[idx].p);
        route.push_back(selected[idx].d);
    }
    route.push_back(o);
    int nn = route.size();
    cout << nn;
    for (auto& pt : route) {
        cout << " " << pt.x << " " << pt.y;
    }
    cout << endl;
    return 0;
}