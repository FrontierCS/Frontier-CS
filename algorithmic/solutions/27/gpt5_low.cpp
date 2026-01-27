#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long n, m;
    if (!(cin >> n >> m)) return 0;

    // We will enforce uniqueness of unordered pairs on the smaller side (ms)
    // and iterate over the larger side (L). This ensures memory is small.
    bool enforceRows = (n <= m); // if true: enforce pairs among rows, iterate columns
    int ms = enforceRows ? (int)n : (int)m;   // size of side we enforce (small side)
    int L  = enforceRows ? (int)m : (int)n;   // number of items on the other side (large side)

    // Special cases
    vector<pair<int,int>> ans;
    ans.reserve((size_t)n * (size_t)m);

    // used matrix for pairs on the small side (1..ms), stored as flattened (ms+1) x (ms+1)
    int stride = ms + 1;
    vector<unsigned char> used((size_t)stride * (size_t)stride, 0);

    auto isUsed = [&](int a, int b) -> bool {
        if (a > b) swap(a, b);
        if (a == b) return false;
        return used[(size_t)a * stride + b];
    };
    auto markUsed = [&](int a, int b) {
        if (a > b) swap(a, b);
        if (a == b) return;
        used[(size_t)a * stride + b] = 1;
    };

    auto comb2 = [&](long long x) -> long long {
        return x * (x - 1) / 2;
    };

    long long totalPairs = comb2(ms);
    long long usedPairs = 0;

    // Order for inner loop to spread selections
    vector<int> innerOrder(ms);
    iota(innerOrder.begin(), innerOrder.end(), 1);

    for (int item = 0; item < L; ++item) {
        long long remainingItems = (L - item);
        long long remainingPairs = totalPairs - usedPairs;
        // Budget pairs for this item
        long long budgetPairsForThis = (remainingItems > 0 ? remainingPairs / remainingItems : 0);

        // Compute cap t such that C(t,2) <= budget
        int tcap = 1;
        if (budgetPairsForThis > 0) {
            // Solve t(t-1)/2 <= B => t^2 - t - 2B <= 0
            long double B = (long double)budgetPairsForThis;
            long double t = floor((1.0L + sqrtl(1.0L + 8.0L * B)) / 2.0L);
            tcap = (int)max(1LL, (long long)t);
            if (comb2(tcap) > budgetPairsForThis) {
                while (tcap > 1 && comb2(tcap) > budgetPairsForThis) --tcap;
            } else {
                while (comb2((long long)tcap + 1) <= budgetPairsForThis) ++tcap;
            }
            // Also cannot exceed ms
            if (tcap > ms) tcap = ms;
        } else {
            tcap = 1;
        }

        vector<int> chosen;
        chosen.reserve(tcap);

        int start = item % ms;
        for (int k = 0; k < ms && (int)chosen.size() < tcap; ++k) {
            int x = innerOrder[(start + k) % ms]; // candidate on small side (1..ms)
            bool ok = true;
            for (int v : chosen) {
                if (isUsed(x, v)) { ok = false; break; }
            }
            if (ok) chosen.push_back(x);
        }

        // Mark pairs used among chosen
        int sz = (int)chosen.size();
        for (int i = 0; i < sz; ++i) {
            for (int j = i + 1; j < sz; ++j) {
                markUsed(chosen[i], chosen[j]);
            }
        }
        usedPairs += comb2(sz);

        // Record coordinates
        if (enforceRows) {
            int c = item + 1;
            for (int r : chosen) ans.emplace_back(r, c);
        } else {
            int r = item + 1;
            for (int c : chosen) ans.emplace_back(r, c);
        }
    }

    cout << ans.size() << '\n';
    for (auto &p : ans) {
        cout << p.first << ' ' << p.second << '\n';
    }
    return 0;
}