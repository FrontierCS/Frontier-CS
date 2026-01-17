#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <map>
#include <tuple>

using namespace std;

int n;
vector<pair<int, int>> adj[101];

int newNode() {
    if (n >= 100) {
        // Fallback, should not happen with proper memoization for the given constraints
    }
    return ++n;
}

// Suffix generator nodes
int U[21]; // U[k] generates any suffix of length k

int end_node;

map<pair<int, int>, int> gr_memo;
map<pair<int, int>, int> le_memo;

int gen_gr_suffix(int val, int rem_len);
int gen_le_suffix(int val, int rem_len);

int gen_gr_suffix(int val, int rem_len) {
    if (rem_len == 0) {
        return end_node;
    }
    int key_val = val & ((1 << rem_len) - 1);
    if (gr_memo.count({key_val, rem_len})) {
        return gr_memo.at({key_val, rem_len});
    }

    int curr = newNode();
    gr_memo[{key_val, rem_len}] = curr;

    int k = rem_len - 1;
    int bit = (val >> k) & 1;

    int target_any = (k > 0) ? U[k] : end_node;

    if (bit == 0) {
        adj[curr].push_back({target_any, 1});
        int next_node = gen_gr_suffix(val, k);
        adj[curr].push_back({next_node, 0});
    } else {
        int next_node = gen_gr_suffix(val, k);
        adj[curr].push_back({next_node, 1});
    }
    return curr;
}

int gen_le_suffix(int val, int rem_len) {
    if (rem_len == 0) {
        return end_node;
    }
    int key_val = val & ((1 << rem_len) - 1);
    if (key_val == (1 << rem_len) - 1) {
        return U[rem_len];
    }
    if (le_memo.count({key_val, rem_len})) {
        return le_memo.at({key_val, rem_len});
    }

    int curr = newNode();
    le_memo[{key_val, rem_len}] = curr;
    
    int k = rem_len - 1;
    int bit = (val >> k) & 1;

    int target_any = (k > 0) ? U[k] : end_node;

    if (bit == 0) {
        int next_node = gen_le_suffix(val, k);
        adj[curr].push_back({next_node, 0});
    } else {
        adj[curr].push_back({target_any, 0});
        int next_node = gen_le_suffix(val, k);
        adj[curr].push_back({next_node, 1});
    }
    return curr;
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int L, R;
    cin >> L >> R;

    n = 1;
    int start_node = 1;
    end_node = newNode();

    int max_len = 0;
    if (R > 0) {
        max_len = floor(log2(R)) + 1;
    }
    
    for (int k = 1; k <= max_len; ++k) {
        U[k] = newNode();
    }
    for (int k = 1; k <= max_len; ++k) {
        int target = (k > 1) ? U[k - 1] : end_node;
        adj[U[k]].push_back({target, 0});
        adj[U[k]].push_back({target, 1});
    }

    int lenL = (L > 0) ? (floor(log2(L)) + 1) : 1;
    int lenR = (R > 0) ? (floor(log2(R)) + 1) : 1;

    for (int k = lenL; k <= lenR; ++k) {
        long long R_k = (1LL << k) - 1;
        long long current_L = max((long long)L, 1LL << (k - 1));
        long long current_R = min((long long)R, R_k);

        if (current_L > current_R) continue;

        if (current_L == (1LL << (k - 1)) && current_R == R_k) {
            int target = (k > 1) ? U[k - 1] : end_node;
            adj[start_node].push_back({target, 1});
        } else {
            int s_k = newNode();
            adj[start_node].push_back({s_k, 1});
            
            int curr = s_k;
            int rem_len = k - 1;
            
            int msb = rem_len - 1;
            while (msb >= 0 && ((current_L >> msb) & 1) == ((current_R >> msb) & 1)) {
                int bit = (current_L >> msb) & 1;
                int next_node = (msb > 0) ? newNode() : end_node;
                adj[curr].push_back({next_node, bit});
                curr = next_node;
                msb--;
            }

            if (msb >= 0) { // Split required
                int L_fork_start = gen_gr_suffix(current_L, msb + 1);
                adj[curr].push_back({L_fork_start, 0});
                
                int R_fork_start = gen_le_suffix(current_R, msb + 1);
                adj[curr].push_back({R_fork_start, 1});
            }
        }
    }
    
    cout << n << endl;
    for (int i = 1; i <= n; ++i) {
        cout << adj[i].size();
        sort(adj[i].begin(), adj[i].end());
        for (auto& edge : adj[i]) {
            cout << " " << edge.first << " " << edge.second;
        }
        cout << endl;
    }

    return 0;
}