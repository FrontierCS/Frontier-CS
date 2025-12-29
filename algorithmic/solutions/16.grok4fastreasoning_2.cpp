#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    cin >> T;
    for (int t = 0; t < T; ++t) {
        long long n;
        cin >> n;
        long long d0 = n / 2;
        vector<long long> refs = {1, 1 + (n / 3), 1 + 2 * (n / 3)};
        long long chosen_r = -1, chosen_s = -1, chosen_d = -1;
        for (auto rr : refs) {
            long long ss = ((rr - 1 + d0) % n) + 1;
            cout << "? " << rr << " " << ss << endl;
            cout.flush();
            long long dd;
            cin >> dd;
            if (dd < d0) {
                chosen_r = rr;
                chosen_s = ss;
                chosen_d = dd;
                break;
            }
        }
        // Now binary search for minimal m
        long long lo = 1, hi = d0;
        while (lo < hi) {
            long long mm = lo + (hi - lo) / 2;
            long long pm = ((chosen_r - 1 + mm) % n) + 1;
            cout << "? " << chosen_r << " " << pm << endl;
            cout.flush();
            long long dm;
            cin >> dm;
            if (dm < mm) {
                hi = mm;
            } else {
                lo = mm + 1;
            }
        }
        long long mm = lo;
        long long pm = ((chosen_r - 1 + mm) % n) + 1;
        // Query de for pm
        cout << "? " << chosen_r << " " << pm << endl;
        cout.flush();
        long long de;
        cin >> de;
        long long temp = de - 1;
        long long c1 = ((chosen_r - 1 + temp) % n) + 1;
        long long c2 = ((chosen_r - 1 - temp + n) % n) + 1;
        vector<long long> cands;
        if (c1 != pm) cands.push_back(c1);
        if (c2 != pm && c2 != c1) cands.push_back(c2);
        bool found = false;
        for (auto c : cands) {
            long long diff = abs(c - pm);
            long long dcyc = min(diff, n - diff);
            if (dcyc < 2) continue;
            cout << "? " << c << " " << pm << endl;
            cout.flush();
            long long dpv;
            cin >> dpv;
            if (dpv == 1) {
                long long uu = min(c, pm);
                long long vv = max(c, pm);
                cout << "! " << uu << " " << vv << endl;
                cout.flush();
                int res;
                cin >> res;
                if (res == -1) {
                    return 0;
                }
                found = true;
                break;
            }
        }
        assert(found);
    }
    return 0;
}