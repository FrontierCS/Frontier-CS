#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>

using namespace std;
using boost::multiprecision::cpp_int;

static inline cpp_int big_abs(const cpp_int& x) { return x < 0 ? -x : x; }

struct Solution {
    vector<int> bits;
    cpp_int sum;
};

void apply_op_add(vector<int>& bits, cpp_int& S, const vector<cpp_int>& a, int i) {
    bits[i] = 1;
    S += a[i];
}
void apply_op_remove(vector<int>& bits, cpp_int& S, const vector<cpp_int>& a, int j) {
    bits[j] = 0;
    S -= a[j];
}
void apply_op_swap(vector<int>& bits, cpp_int& S, const vector<cpp_int>& a, int i, int j) {
    bits[i] = 1;
    bits[j] = 0;
    S += a[i];
    S -= a[j];
}

void local_improve(vector<int>& bits, cpp_int& S, const vector<cpp_int>& a, const cpp_int& W, int K = 60, int max_iter = 2) {
    int n = (int)a.size();
    cpp_int bestDiff = big_abs(W - S);
    for (int it = 0; it < max_iter; ++it) {
        bool improved = false;
        cpp_int diffCur = big_abs(W - S);

        vector<int> selected, notsel;
        selected.reserve(n);
        notsel.reserve(n);
        for (int i = 0; i < n; ++i) {
            if (bits[i]) selected.push_back(i);
            else notsel.push_back(i);
        }

        int mSel = (int)selected.size();
        int mNot = (int)notsel.size();

        // Prepare candidates
        vector<pair<cpp_int,int>> candAdd;
        vector<pair<cpp_int,int>> candRm;

        if (S <= W) {
            cpp_int remain = W - S;
            candAdd.reserve(mNot);
            for (int idx : notsel) {
                cpp_int metric = big_abs(remain - a[idx]);
                candAdd.emplace_back(metric, idx);
            }
            candRm.reserve(mSel);
            for (int idx : selected) {
                cpp_int metric = big_abs(W - (S - a[idx]));
                candRm.emplace_back(metric, idx);
            }
            sort(candAdd.begin(), candAdd.end(), [](const auto& x, const auto& y){
                if (x.first != y.first) return x.first < y.first;
                return x.second < y.second;
            });
            sort(candRm.begin(), candRm.end(), [](const auto& x, const auto& y){
                if (x.first != y.first) return x.first < y.first;
                return x.second < y.second;
            });
        } else {
            cpp_int overshoot = S - W;
            candRm.reserve(mSel);
            for (int idx : selected) {
                cpp_int metric = big_abs(overshoot - a[idx]);
                candRm.emplace_back(metric, idx);
            }
            // For addition under overshoot, prefer small ai for swaps
            vector<pair<cpp_int,int>> allAdd; allAdd.reserve(mNot);
            for (int idx : notsel) {
                allAdd.emplace_back(a[idx], idx);
            }
            sort(candRm.begin(), candRm.end(), [](const auto& x, const auto& y){
                if (x.first != y.first) return x.first < y.first;
                return x.second < y.second;
            });
            sort(allAdd.begin(), allAdd.end(), [](const auto& x, const auto& y){
                if (x.first != y.first) return x.first < y.first;
                return x.second < y.second;
            });
            if ((int)allAdd.size() > K) allAdd.resize(K);
            candAdd = move(allAdd);
        }

        if ((int)candAdd.size() > K) candAdd.resize(K);
        if ((int)candRm.size() > K) candRm.resize(K);

        // Evaluate candidates
        cpp_int bestNewS = S;
        int opType = 0; // 0 none, 1 add, 2 remove, 3 swap
        int bestI = -1, bestJ = -1;
        cpp_int curBestDiff = diffCur;

        if (S <= W) {
            // Add-only
            for (auto &p : candAdd) {
                int i = p.second;
                cpp_int S2 = S + a[i];
                cpp_int d2 = big_abs(W - S2);
                if (d2 < curBestDiff) {
                    curBestDiff = d2;
                    bestNewS = S2;
                    opType = 1; bestI = i; bestJ = -1;
                }
            }
            // Remove-only
            for (auto &p : candRm) {
                int j = p.second;
                cpp_int S2 = S - a[j];
                cpp_int d2 = big_abs(W - S2);
                if (d2 < curBestDiff) {
                    curBestDiff = d2;
                    bestNewS = S2;
                    opType = 2; bestI = -1; bestJ = j;
                }
            }
            // Swap
            for (auto &pa : candAdd) {
                int i = pa.second;
                for (auto &pr : candRm) {
                    int j = pr.second;
                    cpp_int S2 = S - a[j] + a[i];
                    cpp_int d2 = big_abs(W - S2);
                    if (d2 < curBestDiff) {
                        curBestDiff = d2;
                        bestNewS = S2;
                        opType = 3; bestI = i; bestJ = j;
                    }
                }
            }
        } else {
            // Remove-only
            for (auto &p : candRm) {
                int j = p.second;
                cpp_int S2 = S - a[j];
                cpp_int d2 = big_abs(W - S2);
                if (d2 < curBestDiff) {
                    curBestDiff = d2;
                    bestNewS = S2;
                    opType = 2; bestI = -1; bestJ = j;
                }
            }
            // Swap (add small + remove appropriate)
            for (auto &pa : candAdd) {
                int i = pa.second;
                for (auto &pr : candRm) {
                    int j = pr.second;
                    cpp_int S2 = S - a[j] + a[i];
                    cpp_int d2 = big_abs(W - S2);
                    if (d2 < curBestDiff) {
                        curBestDiff = d2;
                        bestNewS = S2;
                        opType = 3; bestI = i; bestJ = j;
                    }
                }
            }
        }

        if (curBestDiff < diffCur) {
            if (opType == 1) {
                apply_op_add(bits, S, a, bestI);
            } else if (opType == 2) {
                apply_op_remove(bits, S, a, bestJ);
            } else if (opType == 3) {
                apply_op_swap(bits, S, a, bestI, bestJ);
            }
            improved = true;
        }

        if (!improved) break;
    }
}

Solution greedy_try(const vector<int>& order, const vector<cpp_int>& a, const cpp_int& W) {
    int n = (int)a.size();
    vector<int> bits(n, 0);
    cpp_int S = 0;

    for (int idx : order) {
        if (S <= W) {
            cpp_int ns = S + a[idx];
            if (ns <= W) {
                bits[idx] = 1;
                S = ns;
            }
        }
    }
    // Optionally add one more item even if overshoots
    cpp_int bestDiff = big_abs(W - S);
    int bestAdd = -1;
    for (int i = 0; i < n; ++i) {
        if (!bits[i]) {
            cpp_int S2 = S + a[i];
            cpp_int d2 = big_abs(W - S2);
            if (d2 < bestDiff) {
                bestDiff = d2;
                bestAdd = i;
            }
        }
    }
    if (bestAdd != -1) {
        bits[bestAdd] = 1;
        S += a[bestAdd];
    }

    local_improve(bits, S, a, W, min(60, n), 2);
    return {bits, S};
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

    // Prepare orders
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);

    vector<vector<int>> orders;

    // Original
    orders.push_back(idx);

    // Reversed
    {
        vector<int> r = idx;
        reverse(r.begin(), r.end());
        orders.push_back(move(r));
    }
    // Increasing
    {
        vector<int> s = idx;
        sort(s.begin(), s.end(), [&](int i, int j){
            if (a[i] != a[j]) return a[i] < a[j];
            return i < j;
        });
        orders.push_back(move(s));
    }
    // Decreasing
    {
        vector<int> s = idx;
        sort(s.begin(), s.end(), [&](int i, int j){
            if (a[i] != a[j]) return a[i] > a[j];
            return i < j;
        });
        orders.push_back(move(s));
    }
    // Random shuffles
    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    for (int t = 0; t < 2; ++t) {
        vector<int> s = idx;
        shuffle(s.begin(), s.end(), rng);
        orders.push_back(move(s));
    }

    // Also consider single-item best solution
    vector<int> best_bits(n, 0);
    cpp_int bestS = 0;
    cpp_int bestDiff = big_abs(W - bestS);

    // Try orders
    for (auto& ord : orders) {
        Solution sol = greedy_try(ord, a, W);
        cpp_int d = big_abs(W - sol.sum);
        if (d < bestDiff) {
            bestDiff = d;
            bestS = sol.sum;
            best_bits = move(sol.bits);
        }
    }

    // Single item best
    for (int i = 0; i < n; ++i) {
        cpp_int d = big_abs(W - a[i]);
        if (d < bestDiff) {
            bestDiff = d;
            bestS = a[i];
            best_bits.assign(n, 0);
            best_bits[i] = 1;
        }
    }

    // Output
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (best_bits[i] ? 1 : 0);
    }
    cout << '\n';
    return 0;
}