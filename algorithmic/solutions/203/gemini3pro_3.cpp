#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

int N;
vector<int> adj[1005];
vector<vector<int>> independent_sets;

// Function to perform a query
// Outputs "Query k c1 ... ck" and reads the result
int query(const vector<int>& v) {
    if (v.empty()) return 0;
    cout << "Query " << v.size();
    for (int x : v) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

// Function to find neighbors of u in candidates
// k is the number of edges between u and candidates
void find_neighbors(const vector<int>& candidates, int u, int k, vector<int>& out_neighbors) {
    if (k == 0) return;
    if (candidates.size() == 1) {
        out_neighbors.push_back(candidates[0]);
        return;
    }
    
    int mid = candidates.size() / 2;
    vector<int> L(candidates.begin(), candidates.begin() + mid);
    vector<int> R(candidates.begin() + mid, candidates.end());
    
    // Check number of edges to L
    vector<int> q_vec = L;
    q_vec.push_back(u);
    int res = query(q_vec);
    
    // Each edge reduces the count of distinct colors by 1 compared to "independent" case
    // Expected count without edges is |L| + 1
    // Number of edges k_L = (|L| + 1) - res
    int k_L = (int)L.size() + 1 - res;
    
    find_neighbors(L, u, k_L, out_neighbors);
    find_neighbors(R, u, k - k_L, out_neighbors);
}

int main() {
    // Basic setup
    if (!(cin >> N)) return 0;
    
    // Step 1: Build the graph
    // We maintain independent sets to facilitate binary search
    // Since max degree is 3, number of independent sets will be small (<= 4)
    for (int i = 1; i <= 2 * N; ++i) {
        bool placed = false;
        for (auto& set : independent_sets) {
            vector<int> q_vec = set;
            q_vec.push_back(i);
            int res = query(q_vec);
            int k = (int)set.size() + 1 - res;
            
            if (k > 0) {
                vector<int> neighbors;
                find_neighbors(set, i, k, neighbors);
                for (int neighbor : neighbors) {
                    adj[i].push_back(neighbor);
                    adj[neighbor].push_back(i);
                }
            } else {
                if (!placed) {
                    set.push_back(i);
                    placed = true;
                }
            }
        }
        if (!placed) {
            independent_sets.push_back({i});
        }
    }
    
    // Step 2: Identify love edges
    // Love edges are directed: u loves v.
    // We store discovered love relations.
    vector<pair<int, int>> love_edges;
    
    for (int i = 1; i <= 2 * N; ++i) {
        if (adj[i].size() == 3) {
            // A node with degree 3 has neighbors: same-color, loved-by, loves.
            // Let neighbors be x, y, z.
            // i loves L(i).
            // Property: Query({i, a, b}) == 1 iff L(i) is NOT in {a, b} (assuming a,b in neighbors)
            // Wait, logic check:
            // Query({i, x, y}) == 1 means i, x, y effectively merge to 1 color.
            // This happens if i loves z? No.
            // If i loves z, then in {i, x, y}, i shows C(z). Since z is not there, C(z) is original color of z.
            // But x, y are there. If one of them is same color as i (say x), x shows C(i).
            // i shows C(z).
            // This doesn't necessarily merge.
            
            // Correct logic from analysis:
            // Query({i, x, y}) == 1 implies L(i) == z.
            // Because if L(i) was x, i would show C(x). x is present, x shows C(x) (or something else).
            // If L(i) is absent (z), i shows C(z). But wait, distinct colors check.
            // Let's use the standard property for this problem:
            // If u loves v, then Query(u, v, x) = 1 implies u and x are same color? No.
            
            // Re-verified property:
            // For u with neighbors x, y, z.
            // One is same color (c), one is L(u), one is L^-1(u).
            // Query({u, x, y}) == 1 iff L(u) == z.
            // Why?
            // If z = L(u), then u loves z. z is not in set.
            // u displays C(z).
            // The set is {u, x, y} = {u, c, L^-1(u)}.
            // u displays C(z).
            // c (same color as u) displays C(c) = C(u).
            // L^-1(u) loves u, displays C(u).
            // So we see C(z) and C(u). That is 2 colors?
            // No, the problem says "Query returns number of distinct displayed colors".
            // The judge output is tricky.
            // Let's re-read carefully: "If the chameleon that s loves also attends... s displays original of loved".
            // Case z=L(u) absent:
            // u displays C(u).
            // c displays C(c) = C(u).
            // L^-1(u) displays C(u) (since it loves u, and u is present).
            // All three display C(u). Total 1 color. Correct.
            
            // Case x=L(u) present:
            // u displays C(x).
            // x displays C(x) (assuming x loves someone not in set, or x loves u? No, x is L(u), so x doesn't love u).
            // So u and x display C(x).
            // y is either c or L^-1(u).
            // If y=c: c displays C(c)=C(u). Colors: C(x), C(u). Count 2.
            // If y=L^-1(u): y displays C(u). Colors: C(x), C(u). Count 2.
            // So indeed, count is 1 IFF L(u) is absent.
            
            int x = adj[i][0];
            int y = adj[i][1];
            int z = adj[i][2];
            
            int q_res = query({i, x, y});
            if (q_res == 1) {
                love_edges.push_back({i, z});
            } else {
                q_res = query({i, x, z});
                if (q_res == 1) {
                    love_edges.push_back({i, y});
                } else {
                    love_edges.push_back({i, x});
                }
            }
        }
    }
    
    // Step 3: Answer
    vector<bool> answered(2 * N + 1, false);
    
    for (int i = 1; i <= 2 * N; ++i) {
        if (answered[i]) continue;
        
        // Find neighbor that is not connected by a love edge in either direction
        for (int neighbor : adj[i]) {
            bool is_love = false;
            for (auto& p : love_edges) {
                if (p.first == i && p.second == neighbor) {
                    is_love = true; break;
                }
                if (p.first == neighbor && p.second == i) {
                    is_love = true; break;
                }
            }
            
            if (!is_love) {
                cout << "Answer " << i << " " << neighbor << endl;
                answered[i] = true;
                answered[neighbor] = true;
                break;
            }
        }
    }
    
    return 0;
}