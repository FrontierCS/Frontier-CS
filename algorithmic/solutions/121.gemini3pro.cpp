#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <iomanip>

using namespace std;

// Global variables
int n, m;
vector<string> patterns;
vector<vector<int>> adj;
vector<bool> visited;
vector<int> component;
long double comp_prob = 0;

// Function to calculate intersection of two patterns
// Returns false if intersection is empty (conflict)
// Otherwise returns true and stores result in res
// Optimization: check validity while building
bool get_intersection(const string& p1, const string& p2, string& res) {
    res.resize(n);
    for (int i = 0; i < n; ++i) {
        char c1 = p1[i];
        char c2 = p2[i];
        if (c1 == '?') {
            res[i] = c2;
        } else if (c2 == '?') {
            res[i] = c1;
        } else if (c1 == c2) {
            res[i] = c1;
        } else {
            return false;
        }
    }
    return true;
}

// Function to check if p1 is a subset of p2 (p1 more specific or equal to p2)
// L(p1) subseteq L(p2)
// This implies p1 matches a subset of strings that p2 matches.
// We keep p2 (the larger set) and discard p1 (subset) for the union problem.
bool is_subset(const string& p1, const string& p2) {
    for (int i = 0; i < n; ++i) {
        if (p2[i] != '?' && p1[i] != p2[i]) return false;
    }
    return true;
}

// DFS for Inclusion-Exclusion
void dfs(int idx, const string& current_pat, int sign) {
    for (int i = idx; i < component.size(); ++i) {
        int p_idx = component[i];
        string next_pat;
        next_pat.resize(n);
        
        bool possible = true;
        int next_fixed = 0;
        
        // Compute intersection and count fixed positions inline
        for(int k=0; k<n; ++k) {
            char c1 = current_pat[k];
            char c2 = patterns[p_idx][k];
            if(c1 == '?') next_pat[k] = c2;
            else if(c2 == '?') next_pat[k] = c1;
            else if(c1 == c2) next_pat[k] = c1;
            else {
                possible = false;
                break;
            }
            if(next_pat[k] != '?') next_fixed++;
        }
        
        if (possible) {
            // Contribution: sign * (1/4)^fixed
            long double term = pow((long double)0.25, next_fixed);
            if (sign == 1) comp_prob += term;
            else comp_prob -= term;
            
            dfs(i + 1, next_pat, -sign);
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    vector<string> raw_patterns(m);
    for (int i = 0; i < m; ++i) {
        cin >> raw_patterns[i];
    }

    // Filter patterns: remove p if p is a subset of q (keep q)
    vector<bool> active(m, true);
    for (int i = 0; i < m; ++i) {
        if (!active[i]) continue;
        for (int j = 0; j < m; ++j) {
            if (i == j) continue;
            if (!active[j]) continue;
            if (is_subset(raw_patterns[i], raw_patterns[j])) {
                // If patterns are identical, remove duplicates (keep one)
                if (raw_patterns[i] == raw_patterns[j]) {
                     if (i > j) {
                         active[i] = false;
                         break; 
                     }
                } else {
                    // i is a proper subset of j, remove i
                    active[i] = false;
                    break;
                }
            }
        }
    }

    patterns.clear();
    for (int i = 0; i < m; ++i) {
        if (active[i]) patterns.push_back(raw_patterns[i]);
    }
    
    m = patterns.size();
    if (m == 0) {
        cout << "0.000000" << endl;
        return 0;
    }

    // Build compatibility graph
    // Two patterns are compatible if they have a non-empty intersection
    adj.assign(m, vector<int>());
    for (int i = 0; i < m; ++i) {
        for (int j = i + 1; j < m; ++j) {
            string temp;
            if (get_intersection(patterns[i], patterns[j], temp)) {
                adj[i].push_back(j);
                adj[j].push_back(i);
            }
        }
    }

    visited.assign(m, false);
    long double total_ans = 0;
    string dummy_start(n, '?'); // Identity element for intersection

    for (int i = 0; i < m; ++i) {
        if (!visited[i]) {
            component.clear();
            vector<int> q;
            q.push_back(i);
            visited[i] = true;
            int head = 0;
            while(head < q.size()){
                int u = q[head++];
                component.push_back(u);
                for(int v : adj[u]){
                    if(!visited[v]){
                        visited[v] = true;
                        q.push_back(v);
                    }
                }
            }

            // Solve component using Inclusion-Exclusion
            comp_prob = 0;
            dfs(0, dummy_start, 1);
            total_ans += comp_prob;
        }
    }

    cout << fixed << setprecision(10) << total_ans << endl;

    return 0;
}