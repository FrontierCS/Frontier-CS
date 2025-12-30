#include <bits/stdc++.h>
using namespace std;

int find_min(int ref, const vector<int>& candidates, int n) {
    if (candidates.empty()) return -1;
    vector<int> current = candidates;
    while (current.size() > 1) {
        vector<int> next_round;
        for (size_t i = 0; i < current.size() / 2; ++i) {
            int aa = current[2 * i];
            int bb = current[2 * i + 1];
            cout << "? " << ref << " " << aa << " " << bb << endl;
            cout.flush();
            int rr;
            cin >> rr;
            vector<pair<int, int>> prs(rr);
            for (int j = 0; j < rr; ++j) {
                int x, y;
                cin >> x >> y;
                if (x > y) swap(x, y);
                prs[j] = {x, y};
            }
            bool has_ref_a = false, has_ref_b = false;
            for (auto p : prs) {
                if (p.first == ref && p.second == aa) has_ref_a = true;
                if (p.first == ref && p.second == bb) has_ref_b = true;
            }
            int winner;
            if (has_ref_a && has_ref_b) {
                winner = min(aa, bb);
            } else if (has_ref_a) {
                winner = aa;
            } else if (has_ref_b) {
                winner = bb;
            } else {
                winner = min(aa, bb);
            }
            next_round.push_back(winner);
        }
        if (current.size() % 2 == 1) {
            next_round.push_back(current.back());
        }
        current = next_round;
    }
    return current[0];
}

int main() {
    int k, n;
    cin >> k >> n;
    vector<int> all_other;
    for (int i = 1; i < n; ++i) all_other.push_back(i);
    int y1 = find_min(0, all_other, n);
    vector<int> remaining;
    for (int i : all_other) if (i != y1) remaining.push_back(i);
    int y2 = find_min(0, remaining, n);
    if (y1 > y2) swap(y1, y2);  // arbitrary, smaller y1 clockwise
    vector<int> others;
    for (int i = 0; i < n; ++i) {
        if (i != 0 && i != y1 && i != y2) others.push_back(i);
    }
    auto comparator = [&](int a, int b) -> bool {
        cout << "? 0 " << a << " " << b << endl;
        cout.flush();
        int rr;
        cin >> rr;
        vector<pair<int, int>> prs(rr);
        for (int j = 0; j < rr; ++j) {
            int x, y;
            cin >> x >> y;
            if (x > y) swap(x, y);
            prs[j] = {x, y};
        }
        bool ha = false, hb = false;
        for (auto p : prs) {
            if (p.first == 0 && p.second == a) ha = true;
            if (p.first == 0 && p.second == b) hb = true;
        }
        if (ha && !hb) return true;
        if (hb && !ha) return false;
        if (ha && hb) return a < b;
        return a < b;  // failure, arbitrary
    };
    sort(others.begin(), others.end(), comparator);
    vector<int> clock_side{y1};
    vector<int> counter_side{y2};
    size_t idx = 0;
    while (idx < others.size()) {
        int a = others[idx];
        bool single = (idx + 1 >= others.size());
        int b = single ? -1 : others[idx + 1];
        idx += single ? 1 : 2;
        int cw, ccw;
        if (single) {
            cw = a;
            ccw = -1;
        } else {
            // query ? y1 a b
            cout << "? " << y1 << " " << a << " " << b << endl;
            cout.flush();
            int rr;
            cin >> rr;
            vector<pair<int, int>> prs(rr);
            for (int j = 0; j < rr; ++j) {
                int x, y;
                cin >> x >> y;
                if (x > y) swap(x, y);
                prs[j] = {x, y};
            }
            bool ha = false, hb = false;
            for (auto p : prs) {
                if (p.first == y1 && p.second == a) ha = true;
                if (p.first == y1 && p.second == b) hb = true;
            }
            if (ha && !hb) {
                cw = a;
                ccw = b;
            } else if (hb && !ha) {
                cw = b;
                ccw = a;
            } else {
                cw = min(a, b);
                ccw = max(a, b);  // arbitrary
            }
        }
        clock_side.push_back(cw);
        if (!single) counter_side.push_back(ccw);
    }
    if (n % 2 == 0 && others.size() % 2 == 1) {
        // the last single already added to clock
    }
    reverse(counter_side.begin(), counter_side.end());
    vector<int> final_order;
    for (int x : counter_side) final_order.push_back(x);
    final_order.push_back(0);
    for (int x : clock_side) final_order.push_back(x);
    cout << "!";
    for (int x : final_order) cout << " " << x;
    cout << endl;
    cout.flush();
    return 0;
}