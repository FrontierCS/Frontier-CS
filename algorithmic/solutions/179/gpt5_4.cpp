#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>

using namespace std;
using boost::multiprecision::cpp_int;

static inline cpp_int absValue(const cpp_int& x) {
    return x < 0 ? -x : x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cpp_int W;
    if (!(cin >> n >> W)) {
        return 0;
    }
    vector<cpp_int> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];

    vector<uint8_t> bestB(n, 0);
    cpp_int bestAbs = absValue(W);

    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);

    // Prepare some orders
    vector<int> ord_desc = idx, ord_asc = idx;
    sort(ord_desc.begin(), ord_desc.end(), [&](int i, int j) {
        if (a[i] == a[j]) return i < j;
        return a[i] > a[j];
    });
    sort(ord_asc.begin(), ord_asc.end(), [&](int i, int j) {
        if (a[i] == a[j]) return i < j;
        return a[i] < a[j];
    });

    auto start = chrono::steady_clock::now();
    // Time limit (adjust conservatively)
    const double TIME_LIMIT_SEC = 1.7;
    auto time_limit = start + chrono::duration<double>(TIME_LIMIT_SEC);

    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto attemptWithOrder = [&](const vector<int>& order) {
        int n = (int)a.size();
        vector<uint8_t> b(n, 0);
        cpp_int R = W; // residual: W - sum
        cpp_int absR = absValue(R);

        // Greedy pass
        for (int id : order) {
            if (chrono::steady_clock::now() >= time_limit) break;
            cpp_int candR = R - a[id];
            if (absValue(candR) < absR) {
                R = candR;
                absR = absValue(R);
                b[id] = 1;
            }
        }

        // 1-opt local improvement (few passes)
        vector<int> perm(n);
        iota(perm.begin(), perm.end(), 0);
        int passes = 0;
        while (passes < 3) {
            if (chrono::steady_clock::now() >= time_limit) break;
            bool improved = false;
            shuffle(perm.begin(), perm.end(), rng);
            for (int id : perm) {
                if (chrono::steady_clock::now() >= time_limit) break;
                cpp_int candR = R + (b[id] ? a[id] : -a[id]); // flip id
                cpp_int candAbs = absValue(candR);
                if (candAbs < absR) {
                    R = candR;
                    absR = candAbs;
                    b[id] ^= 1;
                    improved = true;
                }
            }
            if (!improved) break;
            ++passes;
        }

        // Limited random 2-opt improvements
        int T = min(5000, 10 * n);
        for (int t = 0; t < T; ++t) {
            if (chrono::steady_clock::now() >= time_limit) break;
            int i = (int)(rng() % n);
            int j = (int)(rng() % (n - 1));
            if (j >= i) ++j;
            cpp_int deltaR = (b[i] ? a[i] : -a[i]) + (b[j] ? a[j] : -a[j]);
            cpp_int candR = R + deltaR;
            cpp_int candAbs = absValue(candR);
            if (candAbs < absR) {
                R = candR;
                absR = candAbs;
                b[i] ^= 1;
                b[j] ^= 1;
            }
        }

        if (absR < bestAbs) {
            bestAbs = absR;
            bestB = std::move(b);
        }
    };

    // Try descending, ascending, and multiple random orders until time runs out
    attemptWithOrder(ord_desc);
    if (chrono::steady_clock::now() < time_limit) attemptWithOrder(ord_asc);

    vector<int> ord_rand = idx;
    while (chrono::steady_clock::now() < time_limit) {
        shuffle(ord_rand.begin(), ord_rand.end(), rng);
        attemptWithOrder(ord_rand);
    }

    // Output result
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (bestB[i] ? 1 : 0);
    }
    cout << '\n';
    return 0;
}