#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    vector<vector<int>> memo(n, vector<int>(n, -1));
    long long queries = 0;

    auto ask = [&](int i, int j) -> int {
        if (i == j) return 0; // Should not happen
        if (memo[i][j] != -1) return memo[i][j];
        cout << "? " << i + 1 << " " << j + 1 << endl;
        cout.flush();
        int ans;
        if (!(cin >> ans)) exit(0);
        if (ans == -1) exit(0);
        memo[i][j] = memo[j][i] = ans;
        ++queries;
        return ans;
    };

    vector<int> cand(n);
    iota(cand.begin(), cand.end(), 0);

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    auto pick_pivot_outside = [&](const vector<int>& cand) -> int {
        vector<char> inC(n, 0);
        for (int x : cand) inC[x] = 1;
        vector<int> outside;
        outside.reserve(n);
        for (int i = 0; i < n; ++i) if (!inC[i]) outside.push_back(i);
        if (!outside.empty()) {
            uniform_int_distribution<int> d(0, (int)outside.size() - 1);
            return outside[d(rng)];
        } else {
            uniform_int_distribution<int> d(0, n - 1);
            return d(rng);
        }
    };

    int step = 0;
    while ((int)cand.size() > 1) {
        int pivot;
        if (step == 0 || (int)cand.size() == n) {
            uniform_int_distribution<int> d(0, n - 1);
            pivot = d(rng);
        } else {
            pivot = pick_pivot_outside(cand);
        }

        int mn = INT_MAX;
        vector<int> vals(cand.size(), -1);
        bool pivotInCand = false;

        for (size_t idx = 0; idx < cand.size(); ++idx) {
            int i = cand[idx];
            if (i == pivot) { pivotInCand = true; continue; }
            int v = ask(i, pivot);
            vals[idx] = v;
            if (v < mn) mn = v;
        }

        vector<int> nxt;
        for (size_t idx = 0; idx < cand.size(); ++idx) {
            int i = cand[idx];
            if (i == pivot) continue;
            if (vals[idx] == mn) nxt.push_back(i);
        }

        if (pivotInCand) {
            // If no shrink occurred (all others matched the min), pivot can't be zero in this scenario.
            if ((int)nxt.size() != (int)cand.size() - 1) {
                nxt.push_back(pivot);
            }
        }

        cand.swap(nxt);
        ++step;
    }

    int pos0 = cand[0];
    vector<int> ans(n, 0);
    for (int i = 0; i < n; ++i) if (i != pos0) ans[i] = ask(pos0, i);

    cout << "! ";
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << endl;
    cout.flush();

    return 0;
}