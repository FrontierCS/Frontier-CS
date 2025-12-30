#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

using namespace std;

// Function to interact with the system
// ops: list of lamp IDs to toggle
// returns: vector of booleans (0 or 1) indicating adjacency status after each op
vector<int> query(const vector<int>& ops) {
    if (ops.empty()) return {};
    cout << ops.size();
    for (int x : ops) cout << " " << x;
    cout << endl;
    
    vector<int> res(ops.size());
    for (int i = 0; i < ops.size(); ++i) {
        cin >> res[i];
    }
    return res;
}

void answer(const vector<int>& p) {
    cout << "-1";
    for (int x : p) cout << " " << x;
    cout << endl;
    exit(0);
}

int n;

int main() {
    int subtask;
    if (!(cin >> subtask >> n)) return 0;

    // Step 1: Find 3 Independent Sets A, B, C
    // We do this by finding MIS sequentially.
    // Query 1: Try adding all 1..n. 
    // Those that don't cause conflict form I1.
    // However, to clear the state for next step, we must toggle them back? 
    // Actually, we can just track the state.
    // Let's assume we start empty.
    
    // We'll perform batches to classify nodes.
    // Batch 1: 1..n. Result gives us I1.
    // But result r_i depends on current S.
    // We define I1: nodes where r_i == 0.
    // We know S ends up with I1 + Garbage. 
    // We need to clear S. The system doesn't auto-clear.
    // We can clear S by toggling everything in I1 + Garbage.
    // We know exactly what's in S: all i where we sent "toggle i".
    // So next batch should start with clearing ops.

    vector<int> p(n);
    iota(p.begin(), p.end(), 1);
    
    // Batch 1
    vector<int> q1 = p;
    vector<int> res1 = query(q1);
    
    vector<int> S_state; // What is currently in S
    vector<int> I1, R1;
    for (int i = 0; i < n; ++i) {
        if (res1[i] == 0) {
            I1.push_back(p[i]);
        } else {
            R1.push_back(p[i]);
        }
        S_state.push_back(p[i]);
    }
    
    // Batch 2: Clear S, then process R1 to find I2
    vector<int> q2 = S_state; // To clear
    for (int x : R1) q2.push_back(x);
    
    vector<int> res2 = query(q2);
    // The first S_state.size() results are for clearing.
    // The rest are for R1.
    
    vector<int> I2, R2;
    for (int i = 0; i < R1.size(); ++i) {
        int r = res2[S_state.size() + i];
        if (r == 0) {
            I2.push_back(R1[i]);
        } else {
            R2.push_back(R1[i]);
        }
    }
    
    // Current S contains elements from R1 processing.
    // We need to clear them for the next phases.
    // Current S contents: I2 + Garbage_from_R1.
    // Garbage_from_R1 are elements in R1 where r==1.
    // I2 are elements in R1 where r==0.
    // Basically, all elements of R1 were toggled ON.
    S_state = R1; 
    
    vector<int> I3 = R2; // As derived, remaining set is independent
    
    vector<int> sets[3] = {I1, I2, I3};
    vector<int> node_set_id(n + 1);
    for (int x : I1) node_set_id[x] = 0;
    for (int x : I2) node_set_id[x] = 1;
    for (int x : I3) node_set_id[x] = 2;

    // Step 2: Determine degrees between sets
    // We need to distinguish if a node has 1 or 2 neighbors in a target set.
    // For each u, d_0 + d_1 + d_2 = 2.
    // We query each set fully to find if degree >= 1.
    
    int degree_ge1[3][n + 1]; // [target_set][u]
    // We need to clear S_state first.
    
    // Optimize: Combine degree queries.
    // Batch 3: Clear S_state. Add I1. Probe I2, I3.
    // Batch 4: Clear I1 (it's in S). Add I2. Probe I1, I3.
    // Batch 5: Clear I2. Add I3. Probe I1, I2.
    
    // Actually simpler: 
    // Q_deg1: Clear S. Add I1. Probe All (or just R1).
    // But probing modifies S. We need to restore S.
    // Probe u: Add u, Check, Remove u.
    
    vector<int> q_deg[3];
    // Fill q_deg
    // We need to manage S state carefully.
    // Let's just assume we start each major step with clean S.
    // We have S_state to clear.
    
    // Helper to generate probe sequence
    auto append_probe = [&](vector<int>& q, const vector<int>& targets) {
        for (int u : targets) {
            q.push_back(u);
            q.push_back(u);
        }
    };
    
    for (int t = 0; t < 3; ++t) {
        // Clear previous state
        for (int x : S_state) q_deg[t].push_back(x);
        
        // Add target set
        for (int x : sets[t]) q_deg[t].push_back(x);
        S_state = sets[t];
        
        // Probe others
        vector<int> others;
        for (int i = 0; i < 3; ++i) if (i != t) {
            for (int x : sets[i]) others.push_back(x);
        }
        append_probe(q_deg[t], others);
    }
    
    // Run degree queries
    for (int t = 0; t < 3; ++t) {
        vector<int> res = query(q_deg[t]);
        // Parse
        // First part: clearing. Ignore.
        // Second part: adding set t. Ignore.
        // Third part: probes.
        // Clearing ops count: previous S_state.size()
        // Adding ops count: sets[t].size()
        int offset = (int)q_deg[t].size() - 2 * (n - (int)sets[t].size());
        
        vector<int> others;
        for (int i = 0; i < 3; ++i) if (i != t) {
            for (int x : sets[i]) others.push_back(x);
        }
        
        for (int i = 0; i < others.size(); ++i) {
            int u = others[i];
            int r = res[offset + 2 * i];
            degree_ge1[t][u] = r;
        }
        for (int x : sets[t]) degree_ge1[t][x] = 0; // No edges within set
    }
    
    // Calculate exact degrees
    int exact_deg[3][n + 1]; // [target_set][u]
    for (int u = 1; u <= n; ++u) {
        int my_set = node_set_id[u];
        int d[3] = {0, 0, 0};
        int sum_ge1 = 0;
        for (int t = 0; t < 3; ++t) if (t != my_set) sum_ge1 += degree_ge1[t][u];
        
        for (int t = 0; t < 3; ++t) {
            if (t == my_set) {
                exact_deg[t][u] = 0;
            } else {
                if (degree_ge1[t][u] == 0) exact_deg[t][u] = 0;
                else {
                    // if sum_ge1 == 2, then we have 1 edge to each of the 2 sets (since total deg=2)
                    // if sum_ge1 == 1, then we have 2 edges to the one set with ge1
                    if (sum_ge1 == 2) exact_deg[t][u] = 1;
                    else exact_deg[t][u] = 2;
                }
            }
        }
    }
    
    // Step 3: Bit queries
    vector<long long> neighbor_sum(n + 1, 0);
    
    for (int k = 0; k < 17; ++k) {
        // For each set t, query intersection with M_k
        // Also need intersection with NOT M_k if degree 2 exists
        
        // We will perform 6 batches per bit: 
        // For each target set T:
        //   Query T \cap M_k
        //   Query T \cap !M_k
        // Probing all other nodes
        
        for (int t = 0; t < 3; ++t) {
            for (int type = 0; type < 2; ++type) { // 0: M_k, 1: !M_k
                vector<int> q;
                // Clear S
                for (int x : S_state) q.push_back(x);
                
                // Construct target subset
                vector<int> target_subset;
                for (int x : sets[t]) {
                    int bit = (x >> k) & 1;
                    if ((type == 0 && bit == 1) || (type == 1 && bit == 0)) {
                        target_subset.push_back(x);
                    }
                }
                
                for (int x : target_subset) q.push_back(x);
                S_state = target_subset;
                
                // Probe others
                vector<int> others;
                for (int i = 0; i < 3; ++i) if (i != t) {
                    for (int x : sets[i]) others.push_back(x);
                }
                append_probe(q, others);
                
                vector<int> res = query(q);
                
                int offset = (int)q.size() - 2 * (int)others.size();
                for (int i = 0; i < others.size(); ++i) {
                    int u = others[i];
                    int r = res[offset + 2 * i];
                    
                    // Logic to update sum
                    // If degree is 1: we only care about type 0 (M_k). If r=1, neighbor has bit k.
                    // If degree is 2: 
                    //   We need sum of bits.
                    //   S1 = res from M_k probe. S0 = res from !M_k probe.
                    //   Sum bits = S1 + (1 - S0).
                    
                    int deg = exact_deg[t][u];
                    if (deg == 1) {
                        if (type == 0 && r == 1) {
                            neighbor_sum[u] += (1LL << k);
                        }
                    } else if (deg == 2) {
                        if (type == 0) { // M_k
                            if (r == 1) neighbor_sum[u] += (1LL << k);
                        } else { // !M_k
                            if (r == 0) neighbor_sum[u] += (1LL << k); // +1 contribution
                        }
                    }
                }
            }
        }
    }
    
    // Step 4: Reconstruct Ring
    // Try to find one neighbor of 1
    // Since we know sum_neighbors[1], if we pick neighbor v, other is sum - v.
    // Validate.
    
    for (int start_node = 2; start_node <= n; ++start_node) {
        vector<int> path;
        path.push_back(1);
        path.push_back(start_node);
        
        vector<bool> visited(n + 1, false);
        visited[1] = true;
        visited[start_node] = true;
        
        bool possible = true;
        int curr = start_node;
        int prev = 1;
        
        for (int i = 0; i < n - 2; ++i) {
            long long next_sum = neighbor_sum[curr];
            int next = (int)(next_sum - prev);
            if (next < 1 || next > n || visited[next]) {
                possible = false;
                break;
            }
            visited[next] = true;
            path.push_back(next);
            prev = curr;
            curr = next;
        }
        
        if (possible) {
            // Check loop closure
            long long last_sum = neighbor_sum[curr];
            int closure = (int)(last_sum - prev);
            if (closure == 1) {
                // Also check consistency for 1
                long long one_sum = neighbor_sum[1];
                if (one_sum - curr == start_node) {
                    answer(path);
                }
            }
        }
    }
    
    return 0;
}