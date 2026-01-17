#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, x;
    cin >> n >> x;
    vector<int> t(n + 1);
    for (int i = 1; i <= n; ++i) cin >> t[i];

    // Original LIS length
    vector<int> tail;
    for (int i = 1; i <= n; ++i) {
        auto it = lower_bound(tail.begin(), tail.end(), t[i]);
        if (it == tail.end()) tail.push_back(t[i]);
        else *it = t[i];
    }
    int orig_lis = (int)tail.size();

    if (x == 0) {
        cout << orig_lis << "\n";
        for (int i = 0; i < 10; ++i) cout << "1 1 0\n";
        return 0;
    }

    vector<ll> diff(n + 2, 0);
    vector<tuple<int, int, ll>> ops;
    bool possible = true;

    for (int i = 1; i <= n - 1; ++i) {
        ll need = max(0LL, (ll)t[i] - t[i + 1] + 1 - diff[i + 1]);
        if (need > 0) {
            while (need > 0 && ops.size() < 10) {
                ll d = min((ll)x, need);
                ops.emplace_back(i + 1, n, d);
                diff[i + 1] += d;
                diff[n + 1] -= d;
                need -= d;
            }
            if (need > 0) {
                possible = false;
                break;
            }
        }
    }

    if (possible) {
        cout << n << "\n";
        for (auto& [l, r, d] : ops) cout << l << " " << r << " " << d << "\n";
        for (int i = (int)ops.size(); i < 10; ++i) cout << "1 1 0\n";
    } else {
        cout << orig_lis << "\n";
        for (int i = 0; i < 10; ++i) cout << "1 1 0\n";
    }

    return 0;
}