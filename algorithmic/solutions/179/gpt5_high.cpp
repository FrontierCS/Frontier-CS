#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>

using namespace std;
using boost::multiprecision::cpp_int;

static inline cpp_int absDiff(const cpp_int& a, const cpp_int& b) {
    return (a >= b) ? (a - b) : (b - a);
}

struct Solution {
    vector<char> sel;
    cpp_int sum;
    cpp_int dist;
};

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

    // Early trivial solutions
    cpp_int sumAll = 0;
    int idxEqual = -1;
    for (int i = 0; i < n; ++i) {
        sumAll += a[i];
        if (a[i] == W) idxEqual = i;
    }
    if (idxEqual != -1) {
        for (int i = 0; i < n; ++i) {
            cout << (i == idxEqual ? '1' : '0') << (i + 1 == n ? '\n' : ' ');
        }
        return 0;
    }
    if (sumAll <= W) {
        for (int i = 0; i < n; ++i) {
            cout << '1' << (i + 1 == n ? '\n' : ' ');
        }
        return 0;
    }

    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);

    auto startTime = chrono::steady_clock::now();
    auto elapsed = [&]() -> double {
        return chrono::duration<double>(chrono::steady_clock::now() - startTime).count();
    };
    const double TIME_LIMIT = 1.8; // seconds, heuristic

    // Best solution tracking
    Solution best;
    best.sel.assign(n, 0);
    best.sum = 0;
    best.dist = absDiff(best.sum, W);

    auto updateBest = [&](const vector<char>& sel, const cpp_int& sum) {
        cpp_int d = absDiff(sum, W);
        if (d < best.dist) {
            best.sel = sel;
            best.sum = sum;
            best.dist = d;
        }
    };

    mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    auto greedyOrder = [&](const vector<int>& order, bool startWithAll, bool doLocal) -> Solution {
        Solution sol;
        sol.sel.assign(n, (char)(startWithAll ? 1 : 0));
        sol.sum = startWithAll ? sumAll : cpp_int(0);
        sol.dist = absDiff(sol.sum, W);

        if (startWithAll) {
            for (int id : order) {
                if (elapsed() > TIME_LIMIT) break;
                cpp_int newSum = sol.sum - a[id];
                cpp_int newDist = absDiff(newSum, W);
                if (newDist < sol.dist) {
                    sol.sel[id] = 0;
                    sol.sum = newSum;
                    sol.dist = newDist;
                }
            }
        } else {
            for (int id : order) {
                if (elapsed() > TIME_LIMIT) break;
                cpp_int newSum = sol.sum + a[id];
                cpp_int newDist = absDiff(newSum, W);
                if (newDist < sol.dist) {
                    sol.sel[id] = 1;
                    sol.sum = newSum;
                    sol.dist = newDist;
                }
            }
        }

        // Local single-flip improvements
        if (doLocal) {
            for (int pass = 0; pass < 2; ++pass) {
                if (elapsed() > TIME_LIMIT) break;
                bool changed = false;
                for (int i = 0; i < n; ++i) {
                    if (elapsed() > TIME_LIMIT) break;
                    cpp_int newSum = sol.sum + (sol.sel[i] ? -a[i] : a[i]);
                    cpp_int newDist = absDiff(newSum, W);
                    if (newDist < sol.dist) {
                        sol.sel[i] = !sol.sel[i];
                        sol.sum = newSum;
                        sol.dist = newDist;
                        changed = true;
                    }
                }
                if (!changed) break;
            }
        }

        return sol;
    };

    // Prepare different orders
    vector<int> order_desc = idx;
    sort(order_desc.begin(), order_desc.end(), [&](int i, int j) {
        if (a[i] != a[j]) return a[i] > a[j];
        return i < j;
    });
    vector<int> order_asc = order_desc;
    reverse(order_asc.begin(), order_asc.end());

    // Order by closeness to W: abs(a[i] - W) ascending
    struct Node { cpp_int diff; int idx; };
    vector<Node> nodes;
    nodes.reserve(n);
    for (int i = 0; i < n; ++i) {
        nodes.push_back(Node{absDiff(a[i], W), i});
    }
    sort(nodes.begin(), nodes.end(), [&](const Node& x, const Node& y) {
        if (x.diff != y.diff) return x.diff < y.diff;
        return x.idx < y.idx;
    });
    vector<int> order_close;
    order_close.reserve(n);
    for (auto &nd : nodes) order_close.push_back(nd.idx);

    // Run deterministic heuristics
    auto run_and_update = [&](const vector<int>& order) {
        if (elapsed() > TIME_LIMIT) return;
        Solution s1 = greedyOrder(order, false, true);
        updateBest(s1.sel, s1.sum);
        if (elapsed() > TIME_LIMIT) return;
        Solution s2 = greedyOrder(order, true, true);
        updateBest(s2.sel, s2.sum);
    };

    run_and_update(order_desc);
    run_and_update(order_asc);
    run_and_update(order_close);

    // Random shuffles while time remains
    vector<int> order_rand = idx;
    int rounds = 0;
    while (elapsed() < TIME_LIMIT && rounds < 200) {
        shuffle(order_rand.begin(), order_rand.end(), rng);
        Solution s = greedyOrder(order_rand, false, true);
        updateBest(s.sel, s.sum);
        if (elapsed() > TIME_LIMIT) break;
        // Occasionally start from all-included
        if ((rounds & 1) == 0) {
            Solution s2 = greedyOrder(order_rand, true, true);
            updateBest(s2.sel, s2.sum);
        }
        rounds++;
    }

    // Limited random pairwise improvements on best (time-limited)
    auto improve_pairs = [&](Solution& sol) {
        int tries = min(2000, n * 12);
        for (int t = 0; t < tries; ++t) {
            if (elapsed() > TIME_LIMIT) break;
            int i = -1, j = -1;
            // pick included i
            for (int k = 0; k < 10; ++k) {
                int cand = (int)(rng() % n);
                if (sol.sel[cand]) { i = cand; break; }
            }
            if (i == -1) {
                // fallback linear scan
                for (int cand = 0; cand < n; ++cand) if (sol.sel[cand]) { i = cand; break; }
                if (i == -1) break;
            }
            // pick not included j
            for (int k = 0; k < 10; ++k) {
                int cand = (int)(rng() % n);
                if (!sol.sel[cand]) { j = cand; break; }
            }
            if (j == -1) {
                for (int cand = 0; cand < n; ++cand) if (!sol.sel[cand]) { j = cand; break; }
                if (j == -1) break;
            }
            cpp_int newSum = sol.sum - a[i] + a[j];
            cpp_int newDist = absDiff(newSum, W);
            if (newDist < sol.dist) {
                sol.sel[i] = 0;
                sol.sel[j] = 1;
                sol.sum = newSum;
                sol.dist = newDist;
            }
        }
    };

    if (elapsed() < TIME_LIMIT) {
        Solution tmp = best;
        improve_pairs(tmp);
        updateBest(tmp.sel, tmp.sum);
    }

    // Output best solution
    for (int i = 0; i < n; ++i) {
        cout << (best.sel[i] ? '1' : '0') << (i + 1 == n ? '\n' : ' ');
    }

    return 0;
}