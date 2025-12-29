#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

using namespace std;

const int MAXN = 300005;
const long long INF = 1e18;

// Fenwick Tree for Range Max Query (returns {max_value, source_index})
struct MaxBIT {
    int n;
    vector<long long> tree;
    vector<int> source; 

    MaxBIT(int n) : n(n), tree(n + 1, -INF), source(n + 1, 0) {}

    void update(int idx, long long val, int src) {
        for (; idx <= n; idx += idx & -idx) {
            if (val > tree[idx]) {
                tree[idx] = val;
                source[idx] = src;
            }
        }
    }

    pair<long long, int> query(int idx) {
        long long res = -INF;
        int src = 0;
        for (; idx > 0; idx -= idx & -idx) {
            if (tree[idx] > res) {
                res = tree[idx];
                src = source[idx];
            }
        }
        return {res, src};
    }
};

// Fenwick Tree for Sum Query
struct SumBIT {
    int n;
    vector<int> tree;

    SumBIT(int n) : n(n), tree(n + 1, 0) {}

    void add(int idx, int val) {
        for (; idx <= n; idx += idx & -idx) {
            tree[idx] += val;
        }
    }

    int query(int idx) {
        int sum = 0;
        for (; idx > 0; idx -= idx & -idx) {
            sum += tree[idx];
        }
        return sum;
    }
};

int n;
int v[MAXN];
int pos[MAXN];
int lsmaller[MAXN];
bool in_S[MAXN];
int prev_val[MAXN];
int orig_bin[MAXN];

struct Move {
    int x, y;
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;
    for (int i = 1; i <= n; ++i) {
        cin >> v[i];
        pos[v[i]] = i;
    }

    // Calculate Lsmaller (number of elements smaller than v[i] to its left)
    SumBIT bit_l(n);
    for (int i = 1; i <= n; ++i) {
        int val = v[i];
        lsmaller[val] = bit_l.query(val - 1);
        bit_l.add(val, 1);
    }

    // MWIS (Maximum Weight Increasing Subsequence)
    // Weight strategy: prioritize length (large constant M), then minimize sum of Lsmaller.
    long long M = (long long)n + 500000LL; 
    
    MaxBIT bit_dp(n);
    vector<long long> dp(n + 1);
    
    int best_end = 0;
    long long max_weight = -1;

    for (int i = 1; i <= n; ++i) {
        int val = v[i];
        long long current_weight = M - lsmaller[val];
        
        pair<long long, int> best_prev = bit_dp.query(val - 1);
        
        if (best_prev.first == -INF) {
            dp[val] = current_weight;
            prev_val[val] = 0;
        } else {
            dp[val] = best_prev.first + current_weight;
            prev_val[val] = best_prev.second;
        }

        bit_dp.update(val, dp[val], val);

        if (dp[val] > max_weight) {
            max_weight = dp[val];
            best_end = val;
        }
    }

    // Reconstruct S
    vector<int> S;
    int curr = best_end;
    while (curr != 0) {
        S.push_back(curr);
        curr = prev_val[curr];
    }
    reverse(S.begin(), S.end());

    for (int x : S) in_S[x] = true;

    // Determine bins for all elements
    // Bin for u is count of s in S such that pos[s] < pos[u].
    int s_count = 0;
    for (int i = 1; i <= n; ++i) {
        int val = v[i];
        if (in_S[val]) {
            s_count++;
        } else {
            orig_bin[val] = s_count;
        }
    }

    // Prepare for moves
    vector<int> U;
    for (int i = 1; i <= n; ++i) if (!in_S[i]) U.push_back(i);
    sort(U.rbegin(), U.rend()); // Process largest to smallest

    SumBIT bit_a(n); // Tracks elements present at original positions
    for (int i = 1; i <= n; ++i) bit_a.add(i, 1);

    int m = S.size();
    SumBIT bit_b(m + 1); // Tracks elements inserted into bins 0..m (mapped to 1..m+1)

    long long total_move_cost = 0;
    vector<Move> moves;

    for (int u : U) {
        // Find target bin k = |S_{<u}|
        auto it = lower_bound(S.begin(), S.end(), u);
        int k = distance(S.begin(), it);
        
        // Calculate current position x
        // x = Rank in A + Rank in B (elements to left)
        // u is in original bin j
        int j = orig_bin[u];
        // All inserted elements in bins 0..j are to the left of u (since inserted at start of bin)
        // For bin j, inserted elements are after s_j, and u is after s_j.
        // Since we process decreasing, inserted elements > u are inserted before previously inserted.
        // Wait, inserted elements in Bin j are placed immediately after s_j.
        // u (in A) is at original position relative to s_j.
        // Since all inserted elements are accumulated at the start of the bin, they are to the left of u.
        
        int x = bit_a.query(pos[u]) + bit_b.query(j + 1); 

        // Calculate target rank y
        int y;
        if (k == 0) {
            y = 1;
        } else {
            int sk = S[k-1];
            // y is immediately after s_k
            // rank of s_k = Rank in A + Rank in B
            // s_k is in Bin k-1 (conceptually end of it).
            // Bins 0..k-1 are to left.
            int rank_sk_A = bit_a.query(pos[sk]);
            int rank_sk_B = bit_b.query(k); // sum of bins 0..k-1
            y = rank_sk_A + rank_sk_B + 1;
        }

        moves.push_back({x, y});
        total_move_cost += y;

        bit_a.add(pos[u], -1);
        bit_b.add(k + 1, 1); // Add to Bin k (index k+1)
    }

    long long final_cost = (total_move_cost + 1) * (long long)(moves.size() + 1);
    cout << final_cost << " " << moves.size() << "\n";
    for (auto p : moves) {
        cout << p.x << " " << p.y << "\n";
    }

    return 0;
}