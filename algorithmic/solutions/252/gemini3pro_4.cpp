#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <set>

using namespace std;

// Helper to print query and get response
// Returns 1 if destination is in S, 0 otherwise.
int query(int u, int k, const vector<int>& S) {
    if (S.empty()) return 0;
    cout << "? " << u << " " << k << " " << S.size();
    for (int x : S) {
        cout << " " << x;
    }
    cout << endl;
    int res;
    cin >> res;
    return res;
}

// Find f(u, k) using binary search over the set of all nodes
int find_dest(int u, int k, int n) {
    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 1);
    
    // Narrow down the candidate set
    while (candidates.size() > 1) {
        int mid = candidates.size() / 2;
        vector<int> left_part(candidates.begin(), candidates.begin() + mid);
        
        if (query(u, k, left_part)) {
            candidates = left_part;
        } else {
            vector<int> right_part(candidates.begin() + mid, candidates.end());
            candidates = right_part;
        }
    }
    return candidates[0];
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // Step 1: Find a node r on the cycle reachable from 1.
    // After n steps, any node must have reached a cycle.
    // So r = f(1, n) is guaranteed to be on the cycle of the component containing 1.
    int r = find_dest(1, n, n);

    // Step 2: Find cycle length L.
    // We iterate k = 1, 2, ... to find the smallest k such that f(r, k) = r.
    int L = -1;
    for (int k = 1; k <= n; ++k) {
        if (query(r, k, {r})) {
            L = k;
            break;
        }
    }

    // Step 3: Identify all nodes on the cycle C.
    // We know r is on C. The nodes are r, f(r, 1), f(r, 2), ..., f(r, L-1).
    // We find them sequentially.
    vector<int> C;
    C.reserve(L);
    C.push_back(r);
    
    int curr = r;
    for (int i = 1; i < L; ++i) {
        curr = find_dest(curr, 1, n);
        C.push_back(curr);
    }

    // Step 4: Determine A.
    // A is the set of nodes u such that starting from u we eventually reach the cycle C.
    // Since f(u, n) is guaranteed to be on a cycle, u is in A if and only if f(u, n) is in C.
    // We can query membership in C.
    // To minimize cost, if |C| is large, we check membership in C^c (complement).
    
    vector<int> all_nodes(n);
    iota(all_nodes.begin(), all_nodes.end(), 1);
    
    set<int> C_set(C.begin(), C.end());
    vector<int> C_complement;
    for (int x : all_nodes) {
        if (C_set.find(x) == C_set.end()) {
            C_complement.push_back(x);
        }
    }

    // Choose the smaller set for queries to reduce cost
    bool query_complement = (C_complement.size() < C.size());
    const vector<int>& S_query = query_complement ? C_complement : C;
    
    vector<int> A;
    
    if (S_query.empty()) {
        // If the query set is empty, we handle based on which set it corresponds to.
        if (query_complement) {
            // C^c is empty => C contains all nodes => A is all nodes
            A = all_nodes;
        } else {
            // C is empty => Impossible as cycle length >= 1
        }
    } else {
        for (int u = 1; u <= n; ++u) {
            int res = query(u, n, S_query);
            
            bool in_C;
            if (query_complement) {
                // If checking complement:
                // res = 1 => f(u, n) in C^c => f(u, n) NOT in C
                // res = 0 => f(u, n) NOT in C^c => f(u, n) in C
                in_C = (res == 0);
            } else {
                // If checking C directly:
                // res = 1 => f(u, n) in C
                // res = 0 => f(u, n) NOT in C
                in_C = (res == 1);
            }
            
            if (in_C) {
                A.push_back(u);
            }
        }
    }

    // Output the result
    cout << "! " << A.size();
    for (int x : A) {
        cout << " " << x;
    }
    cout << endl;

    return 0;
}