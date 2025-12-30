#include <iostream>
#include <vector>
#include <algorithm>
#include <functional>

using namespace std;

typedef long long ll;

const int MAXN = 300005;

// Segment Tree for (length, sum) pairs
pair<int, ll> seg_tree[4 * MAXN];
int seg_val[4 * MAXN];

pair<int, ll> max_pair(const pair<int, ll>& a, const pair<int, ll>& b) {
    if (a.first != b.first) {
        return a.first > b.first ? a : b;
    }
    return a.second > b.second ? a : b;
}

void update_seg_tree(int node, int start, int end, int idx, pair<int, ll> val, int v_val) {
    if (start == end) {
        if (max_pair(seg_tree[node], val) == val) {
            seg_tree[node] = val;
            seg_val[node] = v_val;
        }
        return;
    }
    int mid = (start + end) / 2;
    if (start <= idx && idx <= mid) {
        update_seg_tree(2 * node, start, mid, idx, val, v_val);
    } else {
        update_seg_tree(2 * node + 1, mid + 1, end, idx, val, v_val);
    }
    
    if (max_pair(seg_tree[2 * node], seg_tree[2 * node + 1]) == seg_tree[2 * node]) {
        seg_tree[node] = seg_tree[2 * node];
        seg_val[node] = seg_val[2 * node];
    } else {
        seg_tree[node] = seg_tree[2 * node + 1];
        seg_val[node] = seg_val[2 * node + 1];
    }
}

pair<pair<int, ll>, int> query_seg_tree(int node, int start, int end, int l, int r) {
    if (r < start || end < l || l > r) {
        return {{0, 0LL}, 0};
    }
    if (l <= start && end <= r) {
        return {seg_tree[node], seg_val[node]};
    }
    int mid = (start + end) / 2;
    auto p1 = query_seg_tree(2 * node, start, mid, l, r);
    auto p2 = query_seg_tree(2 * node + 1, mid + 1, end, l, r);
    
    if (max_pair(p1.first, p2.first) == p1.first) {
        return p1;
    }
    return p2;
}

int v_arr[MAXN];
int pred[MAXN];
vector<ll> max_sum_for_len;
vector<int> last_val_for_len;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    for (int i = 0; i < n; ++i) {
        cin >> v_arr[i];
    }
    
    max_sum_for_len.resize(n + 1, 0);
    last_val_for_len.resize(n + 1, 0);

    for (int i = 0; i < n; ++i) {
        int v = v_arr[i];
        auto res = query_seg_tree(1, 1, n, 1, v - 1);
        int best_len = res.first.first;
        ll best_sum = res.first.second;
        int prev_val = res.second;

        int new_len = best_len + 1;
        ll new_sum = best_sum + v;
        pred[v] = prev_val;
        
        update_seg_tree(1, 1, n, v, {new_len, new_sum}, v);
        
        if (new_sum > max_sum_for_len[new_len]) {
            max_sum_for_len[new_len] = new_sum;
            last_val_for_len[new_len] = v;
        }
    }

    ll min_final_cost;
    int best_k;

    // Case k = 0
    ll num_moves_k0 = n;
    ll total_cost_k0 = n;
    min_final_cost = (total_cost_k0 + 1) * (num_moves_k0 + 1);
    best_k = 0;

    for (int k = 1; k <= n; ++k) {
        if (max_sum_for_len[k] == 0) continue;

        ll sum_s = max_sum_for_len[k];
        ll num_moves = n - k;
        
        ll total_cost = (ll)n - k + (ll)n * k - sum_s - (ll)k * (k - 1) / 2;
        ll final_cost = (total_cost + 1) * (num_moves + 1);

        if (final_cost < min_final_cost) {
            min_final_cost = final_cost;
            best_k = k;
        }
    }
    
    cout << min_final_cost << " " << n - best_k << endl;

    vector<bool> is_stayer(n + 1, false);
    if (best_k > 0) {
        int curr_v = last_val_for_len[best_k];
        for (int i = 0; i < best_k; ++i) {
            is_stayer[curr_v] = true;
            curr_v = pred[curr_v];
        }
    }

    vector<int> movers;
    for (int i = 1; i <= n; ++i) {
        if (!is_stayer[i]) {
            movers.push_back(i);
        }
    }
    sort(movers.rbegin(), movers.rend());

    vector<pair<int, int>> moves_to_print;
    if (!movers.empty()) {
        vector<int> s_sorted;
        for (int i = 1; i <= n; ++i) {
            if (is_stayer[i]) s_sorted.push_back(i);
        }

        vector<int> p(v_arr, v_arr + n);
        
        for (int m : movers) {
            auto it = lower_bound(s_sorted.begin(), s_sorted.end(), m);
            int y = (it - s_sorted.begin()) + 1;
            
            int x = -1;
            for(size_t i=0; i < p.size(); ++i){
                if(p[i] == m){
                    x = i + 1;
                    break;
                }
            }
            
            moves_to_print.push_back({x, y});
            
            p.erase(p.begin() + x - 1);
            p.insert(p.begin() + y - 1, m);
        }
    }
    
    for(const auto& move : moves_to_print) {
        cout << move.first << " " << move.second << endl;
    }

    return 0;
}