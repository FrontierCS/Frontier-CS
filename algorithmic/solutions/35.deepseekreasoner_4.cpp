#include <bits/stdc++.h>
using namespace std;

const int TOTAL_INDICES = 599;
const int BITS = 16;
const int WEIGHT = 8;

int codes[TOTAL_INDICES];
vector<int> sets[BITS];

void precompute() {
    int cnt = 0;
    for (int mask = 0; mask < (1 << BITS); ++mask) {
        if (__builtin_popcount(mask) == WEIGHT) {
            codes[cnt] = mask;
            if (++cnt == TOTAL_INDICES) break;
        }
    }
    for (int j = 0; j < BITS; ++j) {
        for (int i = 0; i < TOTAL_INDICES; ++i) {
            if (codes[i] >> j & 1) {
                sets[j].push_back(i + 1);
            }
        }
    }
}

void solve() {
    int n;
    cin >> n;
    if (n == -1) exit(0);
    int ans[301][BITS] = {0};
    for (int j = 0; j < BITS; ++j) {
        const auto& S = sets[j];
        int sz = S.size();
        for (int x = 1; x <= n; ++x) {
            cout << "? " << x << " " << sz;
            for (int idx : S) {
                cout << " " << idx;
            }
            cout << endl;
            cout.flush();
            int r;
            cin >> r;
            if (r == -1) exit(0);
            ans[x][j] = r;
        }
    }
    int unique_num = -1;
    for (int x = 1; x <= n; ++x) {
        int weight = 0;
        for (int j = 0; j < BITS; ++j) weight += ans[x][j];
        if (weight == WEIGHT) {
            unique_num = x;
        }
    }
    cout << "! " << unique_num << endl;
    cout.flush();
}

int main() {
    precompute();
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}