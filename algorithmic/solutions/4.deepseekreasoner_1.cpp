#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

const int MAXN = 2005;

int n;
ll k;
vector<ll> known_val[MAXN];
vector<bool> known[MAXN];

ll query(int x, int y) {
    if (known[x][y]) return known_val[x][y];
    cout << "QUERY " << x << " " << y << endl;
    ll v;
    cin >> v;
    known_val[x][y] = v;
    known[x][y] = true;
    return v;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n >> k;

    for (int i = 1; i <= n; i++) {
        known_val[i].resize(n + 1, 0);
        known[i].resize(n + 1, false);
    }

    vector<int> L(n + 1, 1), R(n + 1, n);
    ll cur_k = k;

    while (true) {
        // compute total candidates and active rows
        ll total_cand = 0;
        vector<int> active;
        for (int i = 1; i <= n; i++) {
            if (L[i] <= R[i]) {
                active.push_back(i);
                total_cand += R[i] - L[i] + 1;
            }
        }

        if (total_cand == 1) {
            ll ans = 0;
            for (int i : active) {
                for (int j = L[i]; j <= R[i]; j++) {
                    ans = query(i, j);
                }
            }
            cout << "DONE " << ans << endl;
            return 0;
        }

        // gather row medians with weights
        vector<pair<ll, ll>> medians; // (value, weight)
        for (int i : active) {
            int mid = L[i] + (R[i] - L[i]) / 2;
            ll val = query(i, mid);
            ll weight = R[i] - L[i] + 1;
            medians.emplace_back(val, weight);
        }

        // compute weighted median
        sort(medians.begin(), medians.end());
        ll half = total_cand / 2;
        ll cum = 0;
        ll M;
        for (auto &p : medians) {
            cum += p.second;
            if (cum >= half) {
                M = p.first;
                break;
            }
        }

        // count <= M and get splits
        vector<int> splits(n + 1, 0);
        ll cnt = 0;
        int col = R[1];
        for (int i = 1; i <= n; i++) {
            if (L[i] > R[i]) {
                splits[i] = L[i] - 1;
                continue;
            }
            if (col > R[i]) col = R[i];
            while (col >= L[i] && query(i, col) > M) {
                col--;
            }
            if (col >= L[i]) {
                int num = col - L[i] + 1;
                cnt += num;
                splits[i] = col;
            } else {
                splits[i] = L[i] - 1;
            }
        }

        // handle degenerate cases
        if (cnt == total_cand) {
            ll min_val = LLONG_MAX;
            for (int i : active) {
                ll v = query(i, L[i]);
                if (v < min_val) min_val = v;
            }
            if (min_val == M) {
                cout << "DONE " << M << endl;
                return 0;
            }
            M = (min_val + M) / 2;
            // recount
            cnt = 0;
            col = R[1];
            for (int i = 1; i <= n; i++) {
                if (L[i] > R[i]) {
                    splits[i] = L[i] - 1;
                    continue;
                }
                if (col > R[i]) col = R[i];
                while (col >= L[i] && query(i, col) > M) {
                    col--;
                }
                if (col >= L[i]) {
                    int num = col - L[i] + 1;
                    cnt += num;
                    splits[i] = col;
                } else {
                    splits[i] = L[i] - 1;
                }
            }
        } else if (cnt == 0) {
            ll max_val = LLONG_MIN;
            for (int i : active) {
                ll v = query(i, R[i]);
                if (v > max_val) max_val = v;
            }
            M = (M + max_val) / 2;
            // recount
            cnt = 0;
            col = R[1];
            for (int i = 1; i <= n; i++) {
                if (L[i] > R[i]) {
                    splits[i] = L[i] - 1;
                    continue;
                }
                if (col > R[i]) col = R[i];
                while (col >= L[i] && query(i, col) > M) {
                    col--;
                }
                if (col >= L[i]) {
                    int num = col - L[i] + 1;
                    cnt += num;
                    splits[i] = col;
                } else {
                    splits[i] = L[i] - 1;
                }
            }
        }

        // update boundaries
        if (cnt >= cur_k) {
            for (int i = 1; i <= n; i++) {
                if (L[i] <= R[i]) {
                    R[i] = splits[i];
                }
            }
        } else {
            for (int i = 1; i <= n; i++) {
                if (L[i] <= R[i]) {
                    L[i] = splits[i] + 1;
                }
            }
            cur_k -= cnt;
        }
    }

    return 0;
}