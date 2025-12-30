#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n, m;
    cin >> n >> m;
    vector<long long> cost(m + 1);
    for (int i = 1; i <= m; i++) {
        cin >> cost[i];
    }
    const int N = 405;
    bitset<N> bs[4005];
    for (int i = 1; i <= n; i++) {
        int k;
        cin >> k;
        for (int j = 0; j < k; j++) {
            int a;
            cin >> a;
            bs[a][i] = 1;
        }
    }
    bitset<N> uncov;
    for (int i = 1; i <= n; i++) {
        uncov[i] = 1;
    }
    vector<int> selected;
    while (uncov.count() > 0) {
        int best_s = -1;
        long long bnum = 0, bden = 0;
        for (int s = 1; s <= m; s++) {
            bitset<N> temp = bs[s] & uncov;
            size_t cnt = temp.count();
            if (cnt == 0) continue;
            long long c = cost[s];
            bool better = false;
            if (best_s == -1) {
                better = true;
            } else {
                long long left = c * bden;
                long long right = bnum * (long long)cnt;
                if (left < right) {
                    better = true;
                } else if (left == right && cnt > bden) {
                    better = true;
                }
            }
            if (better) {
                best_s = s;
                bnum = c;
                bden = cnt;
            }
        }
        if (best_s == -1) {
            // Cannot cover, assume always possible
            break;
        }
        selected.push_back(best_s);
        uncov &= ~bs[best_s];
    }
    cout << selected.size() << '\n';
    sort(selected.begin(), selected.end());
    for (int x : selected) {
        cout << x << ' ';
    }
    cout << '\n';
    return 0;
}