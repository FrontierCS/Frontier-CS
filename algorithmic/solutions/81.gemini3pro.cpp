#include <iostream>
#include <vector>
#include <string>
#include <cstdlib>
#include <ctime>
#include <algorithm>
#include <queue>

using namespace std;

int N;

// Function to perform a query
int query(int m, const vector<int>& a, const vector<int>& b) {
    cout << m << " ";
    for (int i = 0; i < m; ++i) cout << a[i] << (i == m - 1 ? "" : " ");
    cout << " ";
    for (int i = 0; i < m; ++i) cout << b[i] << (i == m - 1 ? "" : " ");
    cout << endl;
    int res;
    cin >> res;
    return res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(time(NULL));

    if (!(cin >> N)) return 0;
    
    string S = "";
    
    // States for sinks
    // We will use state 0 as Sink0 and state 1 as Sink1
    // The working states will be 2 to m-1.
    // However, the problem requires outputting 1 to ask a query, 0 to guess.
    // The format is:
    // '1' indicates query.
    // Then m, a, b.
    // We need to print '1' before each query.
    
    // M limit is 102 for full points. Let's use M=100.
    int M = 100;
    int SINK0 = 0;
    int SINK1 = 1;
    
    // Determine characters one by one
    for (int k = 0; k < N; ++k) {
        // We know S[0...k-1]. We want S[k].
        // We will try to find a random DFA configuration that is "safe".
        
        int best_dist = -1;
        vector<int> best_a, best_b;
        int best_target_bit = -1; // 0 or 1
        
        // Try multiple random configurations
        for (int iter = 0; iter < 200; ++iter) {
            // Construct a random DFA
            vector<int> a(M), b(M);
            // Initialize sinks
            a[SINK0] = b[SINK0] = SINK0;
            a[SINK1] = b[SINK1] = SINK1;
            
            // Random transitions for others
            // To improve safety, direct undefined edges to a "Safe" place.
            // But we don't know which are undefined yet.
            // Let's just randomize first.
            for (int i = 2; i < M; ++i) {
                a[i] = 2 + rand() % (M - 2);
                b[i] = 2 + rand() % (M - 2);
            }
            
            // Trace prefix
            int curr = 2; // Start at a working state, say 2.
            // We need to adjust start state logic?
            // The machine starts at 0.
            // So we must use 0 as start.
            // But 0 is Sink0.
            // So we need to remap sinks.
            // Let's use M-2 and M-1 as sinks.
            int REAL_SINK0 = M - 2;
            int REAL_SINK1 = M - 1;
            // Re-init
            for (int i = 0; i < M; ++i) {
                 if (i == REAL_SINK0) { a[i] = b[i] = REAL_SINK0; continue; }
                 if (i == REAL_SINK1) { a[i] = b[i] = REAL_SINK1; continue; }
                 a[i] = rand() % (M - 2);
                 b[i] = rand() % (M - 2);
            }
            
            // Trace
            curr = 0;
            bool possible = true;
            // Track usage
            vector<bool> visited_with_0(M, false);
            vector<bool> visited_with_1(M, false);
            
            // Keep track of edges used in P
            vector<vector<int>> adj(M);
            
            for (char c : S) {
                if (c == '0') {
                    visited_with_0[curr] = true;
                    adj[curr].push_back(a[curr]);
                    curr = a[curr];
                } else {
                    visited_with_1[curr] = true;
                    adj[curr].push_back(b[curr]);
                    curr = b[curr];
                }
                if (curr == REAL_SINK0 || curr == REAL_SINK1) {
                    // Should not happen with random generation in range [0, M-3]
                    possible = false; break;
                }
            }
            
            if (!possible) continue;
            
            int u = curr;
            
            // Check if we can probe 0
            bool can_probe_0 = !visited_with_0[u];
            // Check if we can probe 1
            bool can_probe_1 = !visited_with_1[u];
            
            if (!can_probe_0 && !can_probe_1) continue;
            
            // Calculate safety distance
            // If probing 0: we set a[u] = REAL_SINK0.
            // If S[k]=1, we go to b[u].
            // We need distance from b[u] to u in the P-graph to be large.
            
            // If probing 1: set b[u] = REAL_SINK1.
            // If S[k]=0, go to a[u]. Distance a[u] to u.
            
            int dist = -1;
            int target = -1;
            
            // Prioritize probing 0 or 1?
            // Choose the one with better distance
            
            if (can_probe_0) {
                // Check distance b[u] -> u
                // BFS in adj
                queue<pair<int, int>> q;
                q.push({b[u], 0});
                vector<int> d(M, -1);
                d[b[u]] = 0;
                int d_u = 10000;
                while (!q.empty()) {
                    pair<int, int> top = q.front(); q.pop();
                    int v = top.first;
                    int dist_v = top.second;
                    if (v == u) {
                        d_u = dist_v;
                        break;
                    }
                    for (int nxt : adj[v]) {
                        if (d[nxt] == -1) {
                            d[nxt] = dist_v + 1;
                            q.push({nxt, dist_v + 1});
                        }
                    }
                }
                if (d_u > dist) {
                    dist = d_u;
                    target = 0;
                }
            }
            
            if (can_probe_1) {
                // Check distance a[u] -> u
                queue<pair<int, int>> q;
                q.push({a[u], 0});
                vector<int> d(M, -1);
                d[a[u]] = 0;
                int d_u = 10000;
                while (!q.empty()) {
                    pair<int, int> top = q.front(); q.pop();
                    int v = top.first;
                    int dist_v = top.second;
                    if (v == u) {
                        d_u = dist_v;
                        break;
                    }
                    for (int nxt : adj[v]) {
                        if (d[nxt] == -1) {
                            d[nxt] = dist_v + 1;
                            q.push({nxt, dist_v + 1});
                        }
                    }
                }
                if (d_u > dist) { // Strictly better or same?
                     dist = d_u;
                     target = 1;
                }
            }
            
            if (dist > best_dist) {
                best_dist = dist;
                best_target_bit = target;
                
                // Finalize transitions
                // Direct all unused edges to Safe Sinks to minimize false positives from "off-path" suffix
                // If we probe 0, we want false positive 0 avoided.
                // False pos 0 comes from hitting REAL_SINK0.
                // REAL_SINK0 is only reachable from u via 0.
                // So if we divert all unused edges to REAL_SINK1, we reduce chance of hitting u?
                // Actually, if we hit REAL_SINK1, we get result != REAL_SINK0.
                // So result != 0 => interpreted as 1.
                // This is safe for Probe 0.
                
                // Copy a, b
                best_a = a;
                best_b = b;
                
                // Apply modifications
                // For all v, if !visited_with_0[v] => a[v] = OtherSink
                // If !visited_with_1[v] => b[v] = OtherSink
                // Exception: at u, we set the probe.
                
                int probe_sink = (best_target_bit == 0) ? REAL_SINK0 : REAL_SINK1;
                int other_sink = (best_target_bit == 0) ? REAL_SINK1 : REAL_SINK0;
                
                for (int i = 0; i < M - 2; ++i) {
                    if (!visited_with_0[i]) best_a[i] = other_sink;
                    if (!visited_with_1[i]) best_b[i] = other_sink;
                }
                
                if (best_target_bit == 0) {
                    best_a[u] = probe_sink;
                } else {
                    best_b[u] = probe_sink;
                }
            }
        }
        
        // Execute query
        cout << "1" << endl;
        int res = query(M, best_a, best_b);
        int REAL_SINK0 = M - 2;
        int REAL_SINK1 = M - 1;
        
        if (best_target_bit == 0) {
            // We probed for 0.
            // If result == REAL_SINK0, then S[k] is likely 0.
            // Else S[k] is 1.
            if (res == REAL_SINK0) S += '0';
            else S += '1';
        } else {
            // We probed for 1.
            // If result == REAL_SINK1, then S[k] is likely 1.
            // Else S[k] is 0.
            if (res == REAL_SINK1) S += '1';
            else S += '0';
        }
    }
    
    cout << "0" << endl;
    cout << S << endl;
    
    return 0;
}