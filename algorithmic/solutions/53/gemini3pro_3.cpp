#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <cstdlib>
#include <ctime>

using namespace std;

// Fast I/O
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

// Function to perform a query
int query(const vector<int>& q) {
    cout << "?";
    for (int x : q) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

// Calculate internal edges count within a sorted set of nodes based on known edges
int calc_internal(const vector<int>& nodes, const vector<pair<int, int>>& edges) {
    int count = 0;
    // For small N, simple iteration is fast enough
    for (const auto& edge : edges) {
        int u = edge.first;
        int v = edge.second;
        // Binary search is valid because nodes is sorted
        if (binary_search(nodes.begin(), nodes.end(), u) && 
            binary_search(nodes.begin(), nodes.end(), v)) {
            // In the query, nodes are placed in increasing order.
            // Edge u->v is counted if u appears before v.
            if (u < v) {
                count++;
            }
        }
    }
    return count;
}

// Global variable for N
int n;
vector<pair<int, int>> known_edges;

// Helper to get Delta
int get_delta(int x, const vector<int>& S, const vector<int>& R) {
    // q1: [1, x, S, R]
    // q2: [1, S, x, R]
    // Delta = q1 - q2
    // We need to carefully construct q1 and q2 including all numbers 1..n
    
    vector<int> q1;
    q1.reserve(n);
    q1.push_back(1);
    q1.push_back(x);
    q1.insert(q1.end(), S.begin(), S.end());
    q1.insert(q1.end(), R.begin(), R.end());
    
    vector<int> q2;
    q2.reserve(n);
    q2.push_back(1);
    q2.insert(q2.end(), S.begin(), S.end());
    q2.push_back(x);
    q2.insert(q2.end(), R.begin(), R.end());
    
    int r1 = query(q1);
    int r2 = query(q2);
    
    return r1 - r2;
}

// Recursive function to find edges
void find_edges(int x, vector<int> S, int delta) {
    if (S.empty()) return;
    
    // If delta is 0, we need to disambiguate "Both" or "Neither"
    if (delta == 0) {
        // Randomized check to detect "Both"
        // Try up to 12 times (2^-12 chance of failure)
        bool found_both = false;
        int trials = 12;
        if (S.size() < 2) trials = 0; // Can't split size 1
        
        for (int t = 0; t < trials; ++t) {
            vector<int> S_sub, S_rem;
            for (int val : S) {
                if (rand() % 2) S_sub.push_back(val);
                else S_rem.push_back(val);
            }
            if (S_sub.empty() || S_rem.empty()) continue;
            
            // Construct R for this sub-query
            // R_sub = R_original + S_rem
            // But we need to construct a valid query.
            // The get_delta function needs S and R.
            // We can reconstruct R from all elements not in {1, x} U S_sub.
            vector<int> current_used(n + 1, 0);
            current_used[1] = 1;
            current_used[x] = 1;
            for (int v : S_sub) current_used[v] = 1;
            vector<int> R_sub;
            for (int i = 1; i <= n; ++i) if (!current_used[i]) R_sub.push_back(i);
            
            int sub_delta = get_delta(x, S_sub, R_sub);
            if (sub_delta != 0) {
                // Found split!
                // S_sub has one, S_rem has the other.
                find_edges(x, S_sub, sub_delta);
                
                // Determine delta for S_rem
                // delta_total = delta_sub + delta_rem => 0 = sub + rem => rem = -sub
                find_edges(x, S_rem, -sub_delta);
                found_both = true;
                break;
            }
        }
        
        if (!found_both) {
            // Assume Neither
            return;
        }
    } else {
        // Delta is 1 or -1
        // 1: Succ in S, Pred not.
        // -1: Pred in S, Succ not.
        
        if (S.size() == 1) {
            if (delta == 1) {
                known_edges.push_back({x, S[0]});
            } else {
                known_edges.push_back({S[0], x});
            }
            return;
        }
        
        // Binary search
        int mid = S.size() / 2;
        vector<int> S_left(S.begin(), S.begin() + mid);
        vector<int> S_right(S.begin() + mid, S.end());
        
        // Construct R for S_left query
        vector<int> current_used(n + 1, 0);
        current_used[1] = 1;
        current_used[x] = 1;
        for (int v : S_left) current_used[v] = 1;
        vector<int> R_left;
        for (int i = 1; i <= n; ++i) if (!current_used[i]) R_left.push_back(i);
        
        int delta_left = get_delta(x, S_left, R_left);
        
        // If delta_left matches target delta (1 or -1), it's in left.
        // If delta_left is 0, it must be in right.
        // (Note: Since we know exactly one is in S, "Both" is impossible in sub-problems)
        
        if (delta_left != 0) {
            find_edges(x, S_left, delta_left);
        } else {
            // Optimization: if not in left, must be in right with same delta
            find_edges(x, S_right, delta);
        }
    }
}

void solve() {
    cin >> n;
    cout << 1 << endl; // k = 1

    known_edges.clear();
    vector<int> S;
    S.push_back(2);
    
    // Sort S to keep consistent with internal calc (though for delta logic it's implicit)
    // Actually get_delta puts S elements in vector order.
    // We should keep S sorted for R construction consistency if needed, but R construction scans 1..n.

    for (int x = 3; x <= n; ++x) {
        // Current S is {2, ..., x-1} (conceptually, though order in vector might vary if not sorted)
        // Let's sort S for determinism
        sort(S.begin(), S.end());
        
        // Construct R = {x+1 ... n}
        // Actually R contains everything not in {1, x} U S.
        // Initially {x+1 ... n} are the only ones.
        vector<int> used(n + 1, 0);
        used[1] = 1;
        used[x] = 1;
        for (int s : S) used[s] = 1;
        vector<int> R;
        for (int i = 1; i <= n; ++i) if (!used[i]) R.push_back(i);
        
        int delta = get_delta(x, S, R);
        find_edges(x, S, delta);
        
        S.push_back(x);
    }
    
    // Reconstruct permutation
    vector<int> p(n + 1, 0);
    vector<int> has_out(n + 1, 0);
    vector<int> has_in(n + 1, 0);
    
    for (const auto& edge : known_edges) {
        p[edge.first] = edge.second;
        has_out[edge.first] = 1;
        has_in[edge.second] = 1;
    }
    
    // Find missing edges involving 1
    // There should be exactly one node u with no outgoing (u -> 1)
    // And one node v with no incoming (1 -> v)
    int u_missing = -1;
    int v_missing = -1;
    
    for (int i = 1; i <= n; ++i) {
        if (!has_out[i]) u_missing = i;
        if (!has_in[i]) v_missing = i;
    }
    
    if (u_missing != -1) p[u_missing] = 1; // Actually we assume target is 1
    // But wait, if u_missing is 1, then p[1] is missing.
    // If u_missing is not 1, then p[u_missing] = 1.
    // If u_missing is 1, then p[1] = ?.
    // Wait, u_missing is the node FROM which we have no edge.
    // If u_missing == 1, then we miss 1 -> ?.
    // If v_missing == 1, then we miss ? -> 1.
    
    // Logic:
    // Any node i != 1 must have p[i] != 1 unless discovered.
    // Wait, we can't discover edges to 1 or from 1 with k=1.
    // So for all i != 1, if we didn't find p[i], then p[i] = 1.
    // For 1, p[1] is the node v which has no incoming edge from others.
    
    for (int i = 2; i <= n; ++i) {
        if (!has_out[i]) p[i] = 1;
    }
    
    // Find p[1]
    // 1 points to the one that has no incoming from 2..n
    for (int i = 2; i <= n; ++i) {
        if (!has_in[i]) {
            p[1] = i;
            break;
        }
    }
    // If p[1] is still 0, it means 1->1, but p_i != i.
    // Or maybe n=1? But n>=4.
    
    cout << "!";
    for (int i = 1; i <= n; ++i) cout << " " << p[i];
    cout << endl;
}

int main() {
    fast_io();
    srand(time(NULL));
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}