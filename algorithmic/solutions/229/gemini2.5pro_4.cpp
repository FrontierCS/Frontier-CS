#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <tuple>

using namespace std;

const long long INF = -1e18; // Use negative infinity for DP initialization

int n;
long long x;
vector<int> t;
vector<int> compressed_t;
int distinct_values;

vector<long long> dp_prev, dp_curr;
vector<int> parent_curr;

void solve(int k, int L, int R, int optL, int optR) {
    if (L > R) {
        return;
    }

    int mid = L + (R - L) / 2;
    long long max_val = INF;
    int opt_j = -1;

    vector<int> M;
    int j_start = max(mid, optL);

    for (int i = mid; i < j_start; ++i) {
        int val = compressed_t[i];
        auto it = lower_bound(M.begin(), M.end(), val);
        if (it == M.end()) {
            M.push_back(val);
        } else {
            *it = val;
        }
    }

    for (int j = j_start; j <= optR; ++j) {
        if (j >= mid) {
            int val = compressed_t[j];
            auto it = lower_bound(M.begin(), M.end(), val);
            if (it == M.end()) {
                M.push_back(val);
            } else {
                *it = val;
            }
        }

        if (dp_prev[j + 1] > INF) {
            long long current_val = (long long)M.size() + dp_prev[j + 1];
            if (current_val > max_val) {
                max_val = current_val;
                opt_j = j;
            }
        }
    }
    dp_curr[mid] = max_val;
    parent_curr[mid] = opt_j;

    solve(k, L, mid - 1, optL, opt_j);
    solve(k, mid + 1, R, opt_j, optR);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> x;
    t.resize(n);
    map<int, int> val_map;
    for (int i = 0; i < n; ++i) {
        cin >> t[i];
        val_map[t[i]] = 0;
    }

    distinct_values = 0;
    for (auto const& [val, ignore] : val_map) {
        val_map[val] = distinct_values++;
    }
    compressed_t.resize(n);
    for (int i = 0; i < n; ++i) {
        compressed_t[i] = val_map[t[i]];
    }

    vector<vector<int>> parents(12, vector<int>(n + 2));
    vector<long long> max_lis_at_k(12);

    dp_prev.assign(n + 2, INF);
    dp_prev[n] = 0;

    for (int k = 1; k <= 11; ++k) {
        dp_curr.assign(n + 2, INF);
        parent_curr.assign(n + 2, -1);
        solve(k, 0, n - 1, 0, n - 1);
        dp_prev = dp_curr;
        parents[k] = parent_curr;
        max_lis_at_k[k] = dp_curr[0];
    }
    
    long long max_len = 0;
    int best_k = 0;
    for (int k = 1; k <= 11; ++k) {
        if (max_lis_at_k[k] > max_len) {
            max_len = max_lis_at_k[k];
            best_k = k;
        }
    }

    cout << max_len << endl;

    vector<int> splits;
    int current_pos = 0;
    for (int k = best_k; k >= 1; --k) {
        int next_split_end = parents[k][current_pos];
        if (next_split_end == -1 || next_split_end == n - 1) {
            splits.push_back(n);
            break;
        }
        splits.push_back(next_split_end + 1);
        current_pos = next_split_end + 1;
    }
    
    vector<tuple<int, int, long long>> ops;
    for (size_t i = 0; i < splits.size() -1; ++i) {
        if (splits[i] < n) {
            ops.emplace_back(splits[i] + 1, n, x);
        }
    }

    for (size_t i = 0; i < 10; ++i) {
        if (i < ops.size()) {
            cout << get<0>(ops[i]) << " " << get<1>(ops[i]) << " " << get<2>(ops[i]) << endl;
        } else {
            cout << 1 << " " << 1 << " " << 0 << endl;
        }
    }

    return 0;
}