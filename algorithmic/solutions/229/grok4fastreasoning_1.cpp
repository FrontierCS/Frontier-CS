#include <bits/stdc++.h>
using namespace std;

int get_lis(const vector<long long>& a) {
    int sz = a.size();
    if (sz <= 0) return 0;
    vector<long long> tail;
    for (auto val : a) {
        auto itr = lower_bound(tail.begin(), tail.end(), val);
        if (itr == tail.end()) {
            tail.push_back(val);
        } else {
            *itr = val;
        }
    }
    return tail.size();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int n;
    long long x;
    cin >> n >> x;
    vector<long long> t(n);
    for (int i = 0; i < n; i++) cin >> t[i];
    vector<int> run_len;
    vector<int> drop_pos;
    int posi = 0;
    while (posi < n) {
        int startp = posi;
        while (posi < n - 1 && t[posi] < t[posi + 1]) posi++;
        run_len.push_back(posi - startp + 1);
        if (posi < n - 1) {
            drop_pos.push_back(posi);
        }
        posi++;
    }
    int mm = run_len.size();
    vector<long long> costs;
    if (mm >= 2) {
        costs.resize(mm - 1);
        for (int j = 0; j < mm - 1; j++) {
            int ii = drop_pos[j];
            long long low = t[ii] - t[ii + 1] + 1;
            if (x == 0) {
                costs[j] = 1LL << 60;
            } else {
                costs[j] = (low + x - 1) / x;
            }
        }
    }
    long long maxll = 0;
    int bl = 0, br = 0;
    if (mm > 0) {
        long long cursum = run_len[0];
        long long curcost = 0;
        int lft = 0;
        maxll = cursum;
        bl = 0;
        br = 0;
        for (int rgt = 1; rgt < mm; rgt++) {
            cursum += run_len[rgt];
            curcost += costs[rgt - 1];
            while (curcost > 10 && lft < rgt) {
                cursum -= run_len[lft];
                curcost -= costs[lft];
                lft++;
            }
            if (cursum > maxll) {
                maxll = cursum;
                bl = lft;
                br = rgt;
            }
        }
    }
    int origlis = get_lis(t);
    bool usemerg = (maxll > (long long)origlis);
    long long claimed = usemerg ? maxll : origlis;
    cout << claimed << '\n';
    vector<tuple<int, int, long long>> opss;
    if (usemerg && bl < br) {
        for (int dd = bl; dd < br; dd++) {
            int ii = drop_pos[dd];
            long long low = t[ii] - t[ii + 1] + 1;
            long long q = low / x;
            long long mmod = low % x;
            for (long long k = 0; k < q; k++) {
                opss.emplace_back(ii + 2, n, x);
            }
            if (mmod > 0) {
                opss.emplace_back(ii + 2, n, mmod);
            }
        }
    }
    while (opss.size() < 10u) {
        opss.emplace_back(1, 1, 0LL);
    }
    for (auto [ll, rr, dd] : opss) {
        cout << ll << " " << rr << " " << dd << '\n';
    }
    return 0;
}