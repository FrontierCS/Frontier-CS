#include <bits/stdc++.h>
using namespace std;

int main() {
    int k, n;
    cin >> k >> n;
    vector<int> sorted_doors;
    auto get_cmp = [&](int x, int y) -> int {
        cout << "? 0 " << x << " " << y << endl;
        cout.flush();
        int r;
        cin >> r;
        bool has0x = false, has0y = false, hasxy = false;
        for (int j = 0; j < r; j++) {
            int a, b;
            cin >> a >> b;
            if (a > b) swap(a, b);
            if (a == 0 && b == x) has0x = true;
            if (a == 0 && b == y) has0y = true;
            if (a == min(x, y) && b == max(x, y)) hasxy = true;
        }
        if (has0x && !has0y) return -1;
        if (has0y && !has0x) return 1;
        if (has0x && has0y) return 0;
        // don't know
        return (x < y) ? -1 : 1;
    };
    auto comp = [&](int x, int y) -> bool {
        return get_cmp(x, y) < 0;
    };
    for (int q = 1; q < n; ++q) {
        auto it = lower_bound(sorted_doors.begin(), sorted_doors.end(), q, comp);
        sorted_doors.insert(it, q);
    }
    // Optional fix: one pass to fix obvious errors
    for (size_t i = 0; i + 1 < sorted_doors.size(); ++i) {
        int c = get_cmp(sorted_doors[i], sorted_doors[i + 1]);
        if (c > 0) {
            swap(sorted_doors[i], sorted_doors[i + 1]);
        }
    }
    // Now build arms
    vector<int> arm1, arm2;
    if (!sorted_doors.empty()) {
        arm1.push_back(sorted_doors[0]);
        if (sorted_doors.size() >= 2) {
            arm2.push_back(sorted_doors[1]);
        }
        int num_paired = (n - 1) / 2;
        int num_assign = num_paired - 1;
        for (int lev = 1; lev <= num_assign; ++lev) {
            int idx = 2 * lev;
            int c = sorted_doors[idx];
            int d = sorted_doors[idx + 1];
            int prev = arm1.back();
            cout << "? " << prev << " " << c << " " << d << endl;
            cout.flush();
            int rr;
            cin >> rr;
            bool with_c = false, with_d = false;
            for (int j = 0; j < rr; ++j) {
                int a, b;
                cin >> a >> b;
                if (a > b) swap(a, b);
                if (a == prev && b == c) with_c = true;
                if (a == prev && b == d) with_d = true;
            }
            int next1 = (with_c && !with_d) ? c : ( (!with_c && with_d) ? d : c );
            int next2 = (next1 == c) ? d : c;
            arm1.push_back(next1);
            arm2.push_back(next2);
        }
    }
    // Now construct order
    vector<int> order;
    order.push_back(0);
    for (int p : arm1) order.push_back(p);
    if (n % 2 == 0 && sorted_doors.size() == n - 1) {
        int opp = sorted_doors.back();
        order.push_back(opp);
    }
    for (int i = (int)arm2.size() - 1; i >= 0; --i) {
        order.push_back(arm2[i]);
    }
    // Output
    cout << "!";
    for (int p : order) {
        cout << " " << p;
    }
    cout << endl;
    cout.flush();
    return 0;
}