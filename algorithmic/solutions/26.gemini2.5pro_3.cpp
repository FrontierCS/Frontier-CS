#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

const long long INF = 1e18;

// Using a segment tree where each node stores a vector of max sums for different IS lengths.
struct Node {
    vector<long long> max_sums;
};

// Merges two vectors of max sums by taking the element-wise maximum.
vector<long long> merge(const vector<long long>& v1, const vector<long long>& v2) {
    int n1 = v1.size();
    int n2 = v2.size();
    int n = max(n1, n2);
    vector<long long> res(n, -INF);
    for (int i = 0; i < n; ++i) {
        long long val1 = (i < n1) ? v1[i] : -INF;
        long long val2 = (i < n2) ? v2[i] : -INF;
        res[i] = max(val1, val2);
    }
    return res;
}

vector<Node> seg_tree;
int N_seg;

// Updates the segment tree at a specific value with a new vector of sums.
void update(int idx, const vector<long long>& new_sums) {
    idx += N_seg;
    seg_tree[idx].max_sums = new_sums;
    for (; idx > 1; idx /= 2) {
        seg_tree[idx / 2].max_sums = merge(seg_tree[idx].max_sums, seg_tree[idx ^ 1].max_sums);
    }
}

// Queries the segment tree for a range of values.
vector<long long> query(int l, int r) { // range [l, r)
    vector<long long> res;
    res.push_back(-INF); 
    for (l += N_seg, r += N_seg; l < r; l /= 2, r /= 2) {
        if (l & 1) res = merge(res, seg_tree[l++].max_sums);
        if (r & 1) res = merge(res, seg_tree[--r].max_sums);
    }
    return res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    vector<int> v(n);
    for (int i = 0; i < n; ++i) {
        cin >> v[i];
    }

    N_seg = 1;
    while (N_seg < n + 1) N_seg *= 2;
    seg_tree.resize(2 * N_seg);
    for(int i = 0; i < 2 * N_seg; ++i) seg_tree[i].max_sums.push_back(-INF);

    vector<vector<long long>> f(n);

    for (int i = 0; i < n; ++i) {
        int val = v[i];
        vector<long long> prev_max_sums = query(0, val);
        
        f[i].push_back(-INF); // 0-indexed length, dummy value
        f[i].push_back(val); // length 1
        
        for (size_t k = 1; k < prev_max_sums.size(); ++k) {
            if (prev_max_sums[k] > -INF/2) {
                f[i].push_back(val + prev_max_sums[k]);
            } else {
                break;
            }
        }
        update(val, f[i]);
    }

    vector<long long> max_sum_k(n + 1, 0);
    vector<long long> final_sums = query(0, n + 1);
    for(size_t k = 1; k < final_sums.size(); ++k) {
        if(final_sums[k] > -INF/2) {
            max_sum_k[k] = final_sums[k];
        }
    }
    
    long long best_final_cost = -1;
    int best_k = -1;

    for (int k = 0; k <= n; ++k) {
        if (k > 0 && max_sum_k[k] == 0) continue;
        
        long long sum_s = max_sum_k[k];
        long long m = n - k;
        
        long long total_sum_all = (long long)n * (n + 1) / 2;
        long long sum_m = total_sum_all - sum_s;
        
        long long cost = sum_m - m * (m - 1) / 2;
        long long final_cost = (cost + 1) * (m + 1);
        
        if (best_k == -1 || final_cost < best_final_cost) {
            best_final_cost = final_cost;
            best_k = k;
        }
    }
    
    cout << best_final_cost << " " << n - best_k << endl;

    if (n - best_k > 0) {
        vector<bool> to_keep(n + 1, false);
        int current_k = best_k;
        long long current_sum = max_sum_k[current_k];
        int last_val = n + 1;
        int last_idx = n;

        for (int k = best_k; k >= 1; --k) {
            for (int i = last_idx - 1; i >= 0; --i) {
                if (v[i] < last_val && f[i].size() > k && f[i][k] == current_sum) {
                    to_keep[v[i]] = true;
                    current_sum -= v[i];
                    last_val = v[i];
                    last_idx = i;
                    break;
                }
            }
        }
        
        vector<int> to_move;
        for (int i = 1; i <= n; ++i) {
            if (!to_keep[i]) {
                to_move.push_back(i);
            }
        }
        sort(to_move.rbegin(), to_move.rend());

        vector<int> current_p = v;
        for (int val_to_move : to_move) {
            int current_pos = -1;
            for(size_t i=0; i<current_p.size(); ++i) {
                if(current_p[i] == val_to_move) {
                    current_pos = i + 1;
                    break;
                }
            }
            
            int dest_pos = 1;
            for(int x : current_p) {
                if (x != val_to_move && x < val_to_move) {
                    dest_pos++;
                }
            }

            cout << current_pos << " " << dest_pos << endl;
            
            vector<int> next_p;
            for(int x : current_p) {
                if(x != val_to_move) next_p.push_back(x);
            }
            next_p.insert(next_p.begin() + dest_pos - 1, val_to_move);
            current_p = next_p;
        }
    }
    return 0;
}