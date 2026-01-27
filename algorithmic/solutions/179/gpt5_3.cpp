#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>

using namespace std;
using boost::multiprecision::cpp_int;

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

    // Prepare indices
    vector<int> order_desc(n);
    iota(order_desc.begin(), order_desc.end(), 0);
    sort(order_desc.begin(), order_desc.end(), [&](int i, int j){
        return a[i] > a[j];
    });

    vector<int> order_asc = order_desc;
    reverse(order_asc.begin(), order_asc.end());

    // Best solution tracking
    vector<uint8_t> best_pick(n, 0), temp_pick(n, 0);
    cpp_int best_diff = W >= 0 ? W : -W; // diff for empty set (sum = 0)
    if (best_diff == 0) {
        for (int i = 0; i < n; ++i) {
            cout << 0 << (i + 1 == n ? '\n' : ' ');
        }
        return 0;
    }

    auto run_greedy_order = [&](const vector<int>& order, vector<uint8_t>& out_pick, cpp_int& out_diff) {
        out_pick.assign(n, 0);
        cpp_int rem = W;
        for (int idx : order) {
            if (a[idx] <= rem) {
                out_pick[idx] = 1;
                rem -= a[idx];
                if (rem == 0) break;
            }
        }
        cpp_int current_diff = rem; // since sum <= W, diff = W - sum = rem
        // Try adding one more item (even if it overshoots) to improve closeness
        if (current_diff != 0) {
            cpp_int best_add_diff = current_diff;
            int best_add_idx = -1;
            for (int i = 0; i < n; ++i) {
                if (out_pick[i]) continue;
                cpp_int d = (a[i] >= rem) ? (a[i] - rem) : (rem - a[i]); // |a[i] - rem|
                if (d < best_add_diff) {
                    best_add_diff = d;
                    best_add_idx = i;
                    if (best_add_diff == 0) break;
                }
            }
            if (best_add_idx != -1 && best_add_diff < current_diff) {
                out_pick[best_add_idx] = 1;
                out_diff = best_add_diff;
                return;
            }
        }
        out_diff = current_diff;
    };

    // Evaluate deterministic orders
    cpp_int cur_diff;
    run_greedy_order(order_desc, temp_pick, cur_diff);
    if (cur_diff < best_diff) {
        best_diff = cur_diff;
        best_pick = temp_pick;
        if (best_diff == 0) {
            for (int i = 0; i < n; ++i) {
                cout << (int)best_pick[i] << (i + 1 == n ? '\n' : ' ');
            }
            return 0;
        }
    }

    run_greedy_order(order_asc, temp_pick, cur_diff);
    if (cur_diff < best_diff) {
        best_diff = cur_diff;
        best_pick = temp_pick;
        if (best_diff == 0) {
            for (int i = 0; i < n; ++i) {
                cout << (int)best_pick[i] << (i + 1 == n ? '\n' : ' ');
            }
            return 0;
        }
    }

    // Randomized passes
    vector<int> rand_order(n);
    iota(rand_order.begin(), rand_order.end(), 0);
    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    int max_passes = 64;
    for (int it = 0; it < max_passes; ++it) {
        shuffle(rand_order.begin(), rand_order.end(), rng);
        run_greedy_order(rand_order, temp_pick, cur_diff);
        if (cur_diff < best_diff) {
            best_diff = cur_diff;
            best_pick = temp_pick;
            if (best_diff == 0) break;
        }
    }

    // Output best selection
    for (int i = 0; i < n; ++i) {
        cout << (int)best_pick[i] << (i + 1 == n ? '\n' : ' ');
    }
    return 0;
}