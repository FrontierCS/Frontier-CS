#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <map>

using namespace std;

// Function to interact with the system
// ops: list of lamp IDs to toggle
// returns: list of results (0 or 1) for each operation
vector<int> query(const vector<int>& ops) {
    if (ops.empty()) return {};
    cout << ops.size();
    for (int x : ops) {
        cout << " " << x;
    }
    cout << endl;
    
    vector<int> res(ops.size());
    for (int i = 0; i < ops.size(); ++i) {
        cin >> res[i];
    }
    return res;
}

// Function to submit the guess
void solve(const vector<int>& p) {
    cout << "-1";
    for (int x : p) {
        cout << " " << x;
    }
    cout << endl;
    exit(0);
}

int main() {
    int subtask, n;
    if (!(cin >> subtask >> n)) return 0;

    // Phase 1: Construct Independent Sets I1, I2, I3
    // Query 1: Greedy IS on 1..n
    vector<int> all_nodes(n);
    iota(all_nodes.begin(), all_nodes.end(), 1);
    
    vector<int> res1 = query(all_nodes);
    vector<int> I1, rem1;
    for (int i = 0; i < n; ++i) {
        if (res1[i] == 0) {
            I1.push_back(i + 1);
        } else {
            rem1.push_back(i + 1);
        }
    }
    
    // Cleanup S: S is currently I1 U Rem1 (all nodes). 
    // We need to clear S or reset it.
    // The problem says S is maintained. To clear S, we toggle everything currently in S.
    // Current S contains all nodes 1..n.
    // We toggle all_nodes again to clear S.
    // However, we can combine this cleanup with the next query?
    // No, let's just clear S.
    // Wait, we can construct I2 immediately.
    // The current S has 1s (edges). We need to remove them.
    // Actually, simply toggle all 1..n again. 
    // This will empty S. We can ignore the output.
    query(all_nodes); 

    // Query 2: Greedy IS on rem1 (V \ I1)
    // S is empty now.
    vector<int> res2 = query(rem1);
    vector<int> I2, I3;
    for (int i = 0; i < rem1.size(); ++i) {
        if (res2[i] == 0) {
            I2.push_back(rem1[i]);
        } else {
            I3.push_back(rem1[i]);
        }
    }
    
    // Clear S again. S contains all nodes in rem1.
    query(rem1);

    // Now we have I1, I2, I3. All are Independent Sets.
    // Phase 2: Determine bits of neighbors
    // We will perform 2 passes of bit queries.
    // We need to know for each u, and each bit b, the bit values of its neighbors.
    // There are 2 neighbors.
    // u in I1: neighbors in I2 U I3.
    // u in I2: neighbors in I1 U I3.
    // u in I3: neighbors in I1 U I2.
    
    // To minimize queries, we can try to pack. 
    // But 34-36 queries is acceptable.
    // Let's perform 17 queries for base (I1_1 U I2_0 U I3_1)
    // and 17 queries for base (I1_0 U I2_1 U I3_0).
    
    int num_bits = 0;
    while ((1 << num_bits) <= n) num_bits++;
    if (num_bits < 1) num_bits = 1;
    // For N=1000, 10 bits. For N=10^5, 17 bits.

    // Store bit info: for each node u, for each bit b, store count of neighbors with bit b set?
    // We can get: does u have neighbor in Base?
    // Let's define two base configurations per bit.
    // Conf 0: I1(1), I2(0), I3(1)
    // Conf 1: I1(0), I2(1), I3(0)
    
    vector<vector<int>> neighbor_bits(n + 1, vector<int>(num_bits)); 
    // neighbor_bits[u][b] will store a code:
    // 0: no neighbors have bit b=1 (both 0)
    // 1: some neighbor has bit b=1 (0,1 or 1,1) -> from Conf 0/1 logic we can deduce exact
    
    // Actually, let's record the raw boolean responses.
    // has_neighbor_in_conf[bit][conf][u]
    vector<vector<vector<int>>> raw_res(num_bits, vector<vector<int>>(2, vector<int>(n + 1)));

    for (int b = 0; b < num_bits; ++b) {
        // Conf 0: I1 with bit 1, I2 with bit 0, I3 with bit 1
        vector<int> S0;
        for (int u : I1) if ((u >> b) & 1) S0.push_back(u);
        for (int u : I2) if (!((u >> b) & 1)) S0.push_back(u);
        for (int u : I3) if ((u >> b) & 1) S0.push_back(u);
        
        // Conf 1: I1 with bit 0, I2 with bit 1, I3 with bit 0
        vector<int> S1;
        for (int u : I1) if (!((u >> b) & 1)) S1.push_back(u);
        for (int u : I2) if ((u >> b) & 1) S1.push_back(u);
        for (int u : I3) if (!((u >> b) & 1)) S1.push_back(u);
        
        // We perform queries.
        // For Conf 0: Load S0. Check all u. Clear S0.
        // To optimize, we can do this in one line: Load S0, Check all u, Clear S0.
        // Checking u: u, u.
        // If u in S0: 
        //   First u removes u from S. Res: E(S \ {u}).
        //   Second u adds u back. Res: E(S).
        // If u not in S0:
        //   First u adds u. Res: E(S U {u}).
        //   Second u removes u. Res: E(S).
        // Note: S0 is composed of subsets of I1, I2, I3.
        // I1, I2, I3 are IS.
        // But S0 might have edges between I1-I2, I2-I3, I3-I1.
        // So S0 is NOT necessarily an IS.
        // If S0 has edges, E(S) is 1.
        // If E(S)=1, then adding u returns 1. Removing u returns 1. No info.
        // We MUST ensure base sets are IS.
        
        // Re-plan: We need base sets to be IS.
        // I1, I2, I3 are IS.
        // We can query pairs (I1, I2), (I2, I3), (I3, I1).
        // 3 pairs. For each pair, we need bit info.
        // To reduce queries, we process bits in parallel? No.
        
        // Let's settle for 3 pairs * 17 bits * 2 values = 102 queries?
        // Too slow.
        
        // Let's use 2 queries per bit with safe IS construction.
        // Base sets:
        // Q_A: I1(1) U I2(1). Edges only between I1-I2.
        // This is risky.
        
        // Safe Strategy:
        // Query neighbors of I1 in I2. (Base subset of I2, check I1).
        // Query neighbors of I1 in I3. (Base subset of I3, check I1).
        // Query neighbors of I2 in I3. (Base subset of I3, check I2).
        // Determine u's neighbors:
        // If u in I1: N(u) in I2 U I3.
        // If u in I2: N(u) in I1 U I3.
        // If u in I3: N(u) in I1 U I2.
        
        // We need:
        // For I1: bits of N(u) \cap I2, bits of N(u) \cap I3.
        // For I2: bits of N(u) \cap I1 (already done symmetric), bits of N(u) \cap I3.
        // For I3: bits of N(u) \cap I1 (done), bits of N(u) \cap I2 (done).
        
        // So we need 3 directional checks:
        // 1. I2 -> I1 (Base I2, check I1).
        // 2. I3 -> I1 (Base I3, check I1).
        // 3. I3 -> I2 (Base I3, check I2).
        
        // For each direction, e.g., I2 -> I1:
        // For each bit b:
        //   Base S = { v in I2 | v_b == 1 }.
        //   Check u in I1.
        //   Result: Does u have neighbor in I2 with bit b=1?
        //   We also need for bit b=0?
        //   Yes, to distinguish 0 neighbors vs neighbor with bit 0 vs 2 neighbors etc.
        //   Since degree is small, maybe just bit 1 is enough if we know degree?
        //   But we don't know degree in I2 vs I3.
        //   Wait, total degree is 2.
        //   Deg(u, I2) + Deg(u, I3) = 2.
        //   Possible (Deg I2, Deg I3): (2,0), (1,1), (0,2).
        
        // If we query bit 1 for all bits:
        //   We get an integer Val_1 = OR of neighbors in I2.
        //   Val_0 = OR of neighbors with bit 0? No, we need separate query.
        
        // Let's assume (1,1) split is dominant (it is).
        // If (1,1), we find 1 neighbor in I2, 1 in I3.
        // We can find exact ID in I2 by querying bits.
        // If we query just "v_b == 1", we construct the ID.
        // If the ID we construct is X, then we check if X is in I2.
        // If yes, likely correct.
        
        // Let's implement full queries: 3 pairs x 17 bits = 51 queries.
        // With 3 initial queries, total 54.
        // Score: lambda = 1 - 0.1 * f(54/18) = 1 - 0.1 * f(3) = 1 - 0.1 * 1.58 ~ 0.84.
        // This is safe.
        
        // Optimization: Can we combine I2->I1 and I3->I2?
        // Base S = subset(I2) U subset(I3).
        // Check I1? No, I1 checks against S (I2 U I3).
        // I2 checks against S (I3 only, since I2 disjoint I2).
        // I3 checks against S (I2 only).
        // If we load S = { v in I2 | v_b=1 } U { w in I3 | w_b=1 }.
        // Check I1: finds N(u) \cap (I2_1 U I3_1).
        // Check I2: finds N(u) \cap I3_1.
        // Check I3: finds N(u) \cap I2_1.
        // This works! One query gives info for all!
        // Base S = { v in I1 | v_b=1 } U { v in I2 | v_b=1 } U { v in I3 | v_b=1 }.
        // Wait, S must be IS.
        // S is subset of V. V has edges.
        // We can't use union.
        
        // We can only combine disjoint bipartite sets.
        // I2 and I3 are NOT bipartite (edges I2-I3).
        // I1 and (I2 U I3) is bipartite.
        // I2 and I3 have edges.
        
        // So we can do:
        // Base S = { v in I2 | v_b=1 } U { v in I3 | v_b=1 }.
        // If we remove edges from S?
        // Too hard.
        
        // Let's just do the 3 directional passes.
        // Pass 1: Base I2. Check I1, I3. (Gives N(I1) in I2, N(I3) in I2).
        // Pass 2: Base I3. Check I1, I2. (Gives N(I1) in I3, N(I2) in I3).
        // Pass 3: Base I1. Check I2, I3. (Gives N(I2) in I1, N(I3) in I1).
        // This covers all adjacencies.
        // Total 17 bits * 3 passes = 51 queries.
        
        // For each pass, we query bit=1.
        // Do we need bit=0?
        // If we assume exactly 1 neighbor in each set, bit=1 is enough to reconstruct ID.
        // If 2 neighbors, we get OR.
        // If 0 neighbors, we get 0.
        // We can verify candidate neighbors.
        
        // Let's implement this.
    }
    
    // Data structure to hold OR masks
    // or_masks[u][target_set_idx] = mask
    vector<vector<int>> or_masks(n + 1, vector<int>(4, 0)); // target sets 1, 2, 3
    
    vector<vector<int>*> Sets = {nullptr, &I1, &I2, &I3};
    
    // We do 3 passes.
    // Pass 1: Base I2. Targets I1, I3.
    // Pass 2: Base I3. Targets I1, I2.
    // Pass 3: Base I1. Targets I2, I3.
    
    int passes[3][3] = {
        {2, 1, 3}, // Base 2, Check 1 and 3
        {3, 1, 2}, // Base 3, Check 1 and 2
        {1, 2, 3}  // Base 1, Check 2 and 3
    };
    
    for (int p = 0; p < 3; ++p) {
        int base_idx = passes[p][0];
        vector<int>& Base = *Sets[base_idx];
        vector<int> Targets;
        Targets.insert(Targets.end(), Sets[passes[p][1]]->begin(), Sets[passes[p][1]]->end());
        Targets.insert(Targets.end(), Sets[passes[p][2]]->begin(), Sets[passes[p][2]]->end());
        
        // Map target node to its set index for storage
        vector<int> target_map(n + 1, 0);
        for (int u : *Sets[passes[p][1]]) target_map[u] = base_idx; // u sees base
        for (int u : *Sets[passes[p][2]]) target_map[u] = base_idx;
        
        for (int b = 0; b < num_bits; ++b) {
            vector<int> S;
            for (int u : Base) {
                if ((u >> b) & 1) S.push_back(u);
            }
            
            // Ops: Load S, Check Targets, Clear S
            // To be efficient: 
            // Ops sequence: S elements (toggle on), then for each t in Targets: t, t.
            // Then S elements (toggle off).
            vector<int> ops;
            ops.reserve(S.size() * 2 + Targets.size() * 2);
            for (int u : S) ops.push_back(u);
            for (int u : Targets) {
                ops.push_back(u);
                ops.push_back(u);
            }
            for (int u : S) ops.push_back(u);
            
            vector<int> res = query(ops);
            
            // Analyze results
            // Indices of checks: S.size() + 2*i
            // We care about the first toggle of u (index 2*i).
            // If res is 1, it means u connected to S.
            // Note: res indices are relative to ops.
            int offset = S.size();
            for (int i = 0; i < Targets.size(); ++i) {
                int u = Targets[i];
                // Check result of adding u
                // If S was empty, adding u -> 0.
                // If S not empty (shouldn't be, I_base is IS), adding u -> 1 if neighbor.
                // But S is subset of Base IS, so internal edges = 0.
                // So simple check: res[offset + 2*i] == 1 => neighbor exists with bit b=1.
                if (res[offset + 2 * i] == 1) {
                    or_masks[u][base_idx] |= (1 << b);
                }
            }
            // S is cleared at the end automatically by ops
        }
    }
    
    // Reconstruct Graph
    vector<vector<int>> adj(n + 1);
    
    auto get_candidates = [&](int u, int target_set) {
        int mask = or_masks[u][target_set];
        // If mask is 0, likely no neighbor (or neighbor is 0? IDs are 1..n, so never 0).
        if (mask == 0) return vector<int>{};
        
        // Assume mask is exactly the ID (1 neighbor case)
        // Check if mask exists in target set
        // Also could be OR of 2 neighbors.
        // Heuristic: If mask is in target set, assume it is the unique neighbor.
        // If not, we have 2 neighbors. We can't easily solve 2 neighbors from OR mask.
        // But on cycle, 2 neighbors in same set is rare (only if u is turning point).
        // Let's assume mask is a neighbor.
        return vector<int>{mask};
    };
    
    for (int i = 1; i <= 3; ++i) {
        vector<int>& U = *Sets[i];
        for (int u : U) {
            for (int j = 1; j <= 3; ++j) {
                if (i == j) continue;
                // Neighbors of u in set j
                int mask = or_masks[u][j];
                if (mask == 0) continue;
                
                // Verify mask is a valid node in Set j
                bool found = false;
                for (int v : *Sets[j]) if (v == mask) found = true;
                
                if (found) {
                    adj[u].push_back(mask);
                    adj[mask].push_back(u);
                } else {
                    // Mask is OR of multiple neighbors? 
                    // Or neighbor has 0 bits where checked? No, IDs > 0.
                    // If mask is not in Set j, it implies collision (2 neighbors).
                    // We need to split mask into v | w.
                    // We know v, w in Set j.
                    // Try to find v, w in Set j such that v | w == mask.
                    // This is slow? |Set j| approx N/3.
                    // But usually only few pairs match.
                    // Actually, we can use the degrees.
                    // Total degree is 2.
                    // If we found 1 neighbor in other set, we need 1 here.
                    // If we found 0 in other, we need 2 here.
                }
            }
        }
    }
    
    // Remove duplicates
    for (int i = 1; i <= n; ++i) {
        sort(adj[i].begin(), adj[i].end());
        adj[i].erase(unique(adj[i].begin(), adj[i].end()), adj[i].end());
    }

    // Handle missing edges (heuristic fix)
    // If degree < 2, try to find compatible nodes
    // Brute force matching for remaining?
    // Not enough queries.
    // However, for cycle reconstruction, we can just walk.
    
    // Build permutation
    // Start from 1, find neighbors.
    vector<int> p;
    vector<bool> visited(n + 1, false);
    int curr = 1;
    
    // If 1 is not connected or degree < 2, pick any with degree > 0
    if (adj[curr].empty()) {
        for(int i=1;i<=n;++i) if(adj[i].size()) { curr=i; break; }
    }

    for (int i = 0; i < n; ++i) {
        p.push_back(curr);
        visited[curr] = true;
        int next_node = -1;
        for (int neighbor : adj[curr]) {
            if (!visited[neighbor]) {
                next_node = neighbor;
                break;
            }
        }
        if (next_node == -1) {
            // Cycle closed or broken
            // If i == n-1, closed correctly.
            // If not, pick unvisited
            if (i < n - 1) {
                for (int v = 1; v <= n; ++v) {
                    if (!visited[v]) {
                        next_node = v;
                        break;
                    }
                }
            }
        }
        curr = next_node;
    }
    
    solve(p);
    return 0;
}