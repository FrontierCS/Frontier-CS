#include <bits/stdc++.h>
using namespace std;

static inline void flushout() {
    cout.flush();
}

pair<long long, int> ask(int l, int r) {
    cout << "? " << l << " " << r << endl;
    flushout();
    long long x; int f;
    if (!(cin >> x >> f)) {
        exit(0);
    }
    if (x == -1) {
        exit(0);
    }
    return {x, f};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<long long> ans(n + 1, 0);
    
    vector<pair<int,int>> segs;
    segs.push_back({1, n});
    
    while (!segs.empty()) {
        auto [l, r] = segs.back();
        segs.pop_back();
        if (l > r) continue;
        
        int p = (l + r) >> 1;
        auto qp = ask(p, p);
        long long x = qp.first;
        
        // Find left boundary within [l, p]
        int lo = l, hi = p, ansLeft = p;
        int fAtAnsLeft = 1; // default from [p,p]
        while (lo <= hi) {
            int mid = (lo + hi) >> 1;
            auto q = ask(mid, p);
            if (q.first == x) {
                ansLeft = mid;
                fAtAnsLeft = q.second;
                hi = mid - 1;
            } else {
                lo = mid + 1;
            }
        }
        int Lsub = p - fAtAnsLeft + 1;
        if (Lsub < l) Lsub = l;
        
        // Find right boundary within [p, r]
        lo = p; hi = r;
        int ansRight = p;
        int fAtAnsRight = 1; // default from [p,p]
        while (lo <= hi) {
            int mid = (lo + hi) >> 1;
            auto q = ask(p, mid);
            if (q.first == x) {
                ansRight = mid;
                fAtAnsRight = q.second;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }
        int Rsub = p + fAtAnsRight - 1;
        if (Rsub > r) Rsub = r;
        
        for (int i = Lsub; i <= Rsub; ++i) ans[i] = x;
        
        if (Lsub - 1 >= l) segs.push_back({l, Lsub - 1});
        if (Rsub + 1 <= r) segs.push_back({Rsub + 1, r});
    }
    
    cout << "! ";
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << ans[i];
    }
    cout << endl;
    flushout();
    return 0;
}