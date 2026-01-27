#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>

using namespace std;
using boost::multiprecision::cpp_int;

static inline cpp_int parseBig(const string& s) {
    cpp_int x = 0;
    for (char c : s) {
        if (c >= '0' && c <= '9') {
            x *= 10;
            x += (int)(c - '0');
        }
    }
    return x;
}

static inline cpp_int abs_cpp(const cpp_int& x) {
    return x >= 0 ? x : -x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    string Ws;
    if (!(cin >> n >> Ws)) {
        return 0;
    }
    cpp_int W = parseBig(Ws);
    vector<cpp_int> a(n);
    for (int i = 0; i < n; ++i) {
        string s; 
        cin >> s;
        a[i] = parseBig(s);
    }

    vector<int> best_sel(n, 0);
    cpp_int best_sum = 0;
    cpp_int best_diff = abs_cpp(W - best_sum);

    // Helper to evaluate and update best
    auto consider = [&](const vector<int>& sel, const cpp_int& sum) {
        cpp_int diff = abs_cpp(W - sum);
        if (diff < best_diff) {
            best_diff = diff;
            best_sel = sel;
            best_sum = sum;
        }
    };

    // Empty set
    {
        vector<int> sel(n, 0);
        consider(sel, 0);
    }

    // All set
    {
        vector<int> sel(n, 1);
        cpp_int sum = 0;
        for (int i = 0; i < n; ++i) sum += a[i];
        consider(sel, sum);
    }

    // Single best item
    {
        int best_idx = -1;
        cpp_int best_single_diff = abs_cpp(W);
        for (int i = 0; i < n; ++i) {
            cpp_int d = abs_cpp(W - a[i]);
            if (d < best_single_diff) {
                best_single_diff = d;
                best_idx = i;
            }
        }
        if (best_idx != -1) {
            vector<int> sel(n, 0);
            sel[best_idx] = 1;
            consider(sel, a[best_idx]);
        }
    }

    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);

    // Monotone improvement over a permutation
    auto run_perm_improve = [&](const vector<int>& order) {
        vector<int> sel(n, 0);
        cpp_int sum = 0;
        cpp_int curr_diff = abs_cpp(W - sum);
        for (int id : order) {
            cpp_int ns = sum + a[id];
            cpp_int nd = abs_cpp(W - ns);
            if (nd <= curr_diff) {
                sel[id] = 1;
                sum = ns;
                curr_diff = nd;
            }
        }
        consider(sel, sum);
    };

    // Greedy fit under W with descending values
    auto run_desc_fit = [&]() {
        vector<int> order = idx;
        sort(order.begin(), order.end(), [&](int i, int j) {
            if (a[i] == a[j]) return i < j;
            return a[i] > a[j];
        });
        vector<int> sel(n, 0);
        cpp_int sum = 0;
        for (int id : order) {
            if (sum + a[id] <= W) {
                sel[id] = 1;
                sum += a[id];
            }
        }
        consider(sel, sum);
    };

    // Prepare permutations: original, ascending, descending
    {
        // Original
        run_perm_improve(idx);

        // Ascending
        vector<int> asc = idx;
        sort(asc.begin(), asc.end(), [&](int i, int j) {
            if (a[i] == a[j]) return i < j;
            return a[i] < a[j];
        });
        run_perm_improve(asc);

        // Descending
        vector<int> desc = idx;
        sort(desc.begin(), desc.end(), [&](int i, int j) {
            if (a[i] == a[j]) return i < j;
            return a[i] > a[j];
        });
        run_perm_improve(desc);

        // Greedy fit under W (descending)
        run_desc_fit();
    }

    // Random permutations
    {
        mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
        vector<int> order = idx;
        int iterations = max(10, min(60, n)); // bounded number of random tries
        for (int it = 0; it < iterations; ++it) {
            shuffle(order.begin(), order.end(), rng);
            run_perm_improve(order);
        }
    }

    // Output best selection
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << best_sel[i];
    }
    cout << '\n';

    return 0;
}