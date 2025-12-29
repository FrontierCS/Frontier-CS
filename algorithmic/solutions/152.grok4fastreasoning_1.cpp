#include <bits/stdc++.h>
using namespace std;

struct point {
    int x, y;
};

int mandist(point a, point b) {
    return abs(a.x - b.x) + abs(a.y - b.y);
}

struct order {
    point p, d;
    int id;
    long long cost;
};

int main() {
    vector<order> all_orders(1000);
    point O = {400, 400};
    for (int i = 0; i < 1000; i++) {
        int a, b, c, d;
        cin >> a >> b >> c >> d;
        all_orders[i].p = {a, b};
        all_orders[i].d = {c, d};
        all_orders[i].id = i + 1;
        all_orders[i].cost = (long long)mandist(O, all_orders[i].p) + mandist(all_orders[i].p, all_orders[i].d) + mandist(all_orders[i].d, O);
    }
    sort(all_orders.begin(), all_orders.end(), [](const order& a, const order& b) {
        return a.cost < b.cost;
    });
    vector<order> selected(all_orders.begin(), all_orders.begin() + 50);
    const int INF = 1e9 + 5;
    point current = O;
    vector<int> seq;
    vector<bool> used(50, false);
    for (int step = 0; step < 50; step++) {
        int best = -1;
        int mind = INF;
        for (int j = 0; j < 50; j++) {
            if (!used[j]) {
                int dd = mandist(current, selected[j].p);
                if (dd < mind || (dd == mind && j < best)) {
                    mind = dd;
                    best = j;
                }
            }
        }
        seq.push_back(best);
        used[best] = true;
        current = selected[best].d;
    }
    vector<int> chosen_ids;
    for (auto& ord : selected) {
        chosen_ids.push_back(ord.id);
    }
    sort(chosen_ids.begin(), chosen_ids.end());
    cout << 50;
    for (int id : chosen_ids) {
        cout << " " << id;
    }
    cout << endl;
    int n = 102;
    cout << n;
    cout << " 400 400";
    for (int i : seq) {
        auto& ord = selected[i];
        cout << " " << ord.p.x << " " << ord.p.y << " " << ord.d.x << " " << ord.d.y;
    }
    cout << " 400 400" << endl;
    return 0;
}