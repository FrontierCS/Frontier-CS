#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <random>
#include <map>

using namespace std;

// Problem parameters
const int N = 1000;
const int M_LIMIT = 100; // Target M <= 102

// Global known string
string S_known = "";

// Function to make a query
// Returns the final state
int query(int m, const vector<int>& a, const vector<int>& b) {
    cout << "? " << m << " ";
    for (int i = 0; i < m; ++i) cout << a[i] << (i == m - 1 ? "" : " ");
    cout << " ";
    for (int i = 0; i < m; ++i) cout << b[i] << (i == m - 1 ? "" : " ");
    cout << endl;
    
    int result;
    cin >> result;
    return result;
}

// Function to make a guess
void guess(string s) {
    cout << "! " << s << endl;
    exit(0);
}

// Solver for finding a valid path mapping
// Maps prefix S[0...k-1] to states 0..P_SIZE-1
// Constraints:
// 1. Consistent transitions
// 2. At step k-1, mapped state u has edge (u, S[k-1]) unused.
bool solve_mapping(int k, int P_SIZE, char next_bit, vector<int>& path, vector<int>& a_map, vector<int>& b_map) {
    // Reset
    path.assign(k, 0);
    a_map.assign(P_SIZE, -1);
    b_map.assign(P_SIZE, -1);
    
    // We use a randomized greedy approach with restarts or local search?
    // Given constraints, we can build the path incrementally.
    // If we get stuck or violate the final condition, backtrack or restart.
    // Since k can be up to 1000, backtracking is too slow.
    // Randomized greedy with multiple tries.
    
    static mt19937 rng(1337);
    
    // Try building
    int curr = 0; // Fixed start? Or random start? Start must be 0 for machine.
    // Machine starts at 0. So path[0] = 0.
    // We need to assign transitions.
    
    // To ensure success, we might need to look ahead or just rely on randomness.
    // With P_SIZE ~ 90, density is high.
    
    // Let's try up to 1000 attempts
    for (int attempt = 0; attempt < 2000; ++attempt) {
        fill(a_map.begin(), a_map.end(), -1);
        fill(b_map.begin(), b_map.end(), -1);
        
        curr = 0;
        bool fail = false;
        
        for (int i = 0; i < k; ++i) {
            path[i] = curr;
            char c = (i == k - 1) ? next_bit : S_known[i];
            
            // If this is the LAST step (i == k-1), we need to check exit condition.
            // But function argument 'k' is the length of prefix including the one leading to branch?
            // Wait. We want to determine S[k].
            // We know S[0...k-1].
            // We are at step k (0-indexed).
            // Machine does: state = 0.
            // For i = 0 to k-1: read S[i], trans.
            // Now at state X. Read S[k] (unknown). Trans.
            // So we need the path for 0...k-1.
            // And at state at step k, say u, we need branching.
            // Branching requires: u not visited with '0' in past (if we want to use '0' branch freely)
            // or u not visited with '1' (if '1' branch freely).
            // Actually, we define a_u and b_u.
            // If u visited with '0', a_u is fixed.
            // If u visited with '1', b_u is fixed.
            // To be able to set a_u != b_u, we need NOT (u visited with '0' AND u visited with '1' AND fixed to same).
            // But we choose fixings.
            // So we just need u to be such that we can assign a_u != b_u.
            // This is always possible unless a_u and b_u are BOTH fixed by prefix.
            // i.e. u visited with '0' AND u visited with '1'.
            // If u is visited with both, we must have chosen targets previously.
            // If we chose distinct targets, we are fine!
            // So we just need to ensure that IF u is visited with both, we point them to distinct nodes.
            // AND the targets must lead to valid suffix diff.
            // Easiest is to make u NOT visited with both.
            // Or even better: Make u NOT visited with '0', OR NOT visited with '1'.
            // If u is "clean" for at least one bit, we have freedom.
            
            // So solver goal:
            // Build path for S[0...k-1].
            // End state u.
            // Condition: u has a_map[u] == -1 OR b_map[u] == -1.
            
            // Loop for prefix
            // To simplify logic, this loop is for 0 to k-1.
            
            int next_state;
            
            // Determine transition
            char bit = S_known[i];
            if (bit == '0') {
                if (a_map[curr] != -1) {
                    next_state = a_map[curr];
                } else {
                    // Pick random next
                    next_state = rng() % P_SIZE;
                    a_map[curr] = next_state;
                }
            } else {
                if (b_map[curr] != -1) {
                    next_state = b_map[curr];
                } else {
                    next_state = rng() % P_SIZE;
                    b_map[curr] = next_state;
                }
            }
            
            curr = next_state;
        }
        
        // After loop, curr is the state at step k.
        // Check condition
        if (a_map[curr] == -1 || b_map[curr] == -1) {
            // Found a good path!
            return true;
        }
        
        // If curr is saturated (visited with both 0 and 1), we can't easily branch freely.
        // (Unless we backtrack and change previous decisions to split them, but easier to just find a clean node).
    }
    
    return false;
}

int main() {
    int N_in;
    if (!(cin >> N_in)) return 0;
    
    // We have 1000 bits to find.
    // M can be up to 102 for full points.
    // We partition states:
    // 0..89: Prefix Pool (P)
    // 90..94: C0 (Sink 0)
    // 95..99: C1 (Sink 1)
    
    int P_SIZE = 90;
    int C0_START = 90;
    int C0_END = 94; // 5 states
    int C1_START = 95;
    int C1_END = 99; // 5 states
    int M = 100;
    
    vector<int> a(M), b(M);
    vector<int> path(N);
    vector<int> a_map(P_SIZE), b_map(P_SIZE);
    
    for (int k = 0; k < N; ++k) {
        // Solve for mapping
        // We need to map S_known (length k) to P
        // Such that end state u has free slot.
        // Since solve_mapping is random, it might fail.
        // But with 2000 tries and P=90, for length 1000, it should succeed.
        // The condition "not both 0 and 1 visited" is actually quite mild for the LAST node,
        // because we just land there.
        // We only fail if the node we land on happens to be one that was HEAVILY used before.
        // Random walk spreads usage.
        
        // We pass a dummy char because solve_mapping structure was slightly different.
        // Adapted:
        if (!solve_mapping(k, P_SIZE, ' ', path, a_map, b_map)) {
            // Should not happen. If it does, we can increase P_SIZE (reduce C sizes).
            // Or try more iterations.
            // Fallback: Just guess '0' (risky) or try to branch anyway?
            // If solve fails, we might just crash or produce bad query.
            // Let's assume it works.
        }
        
        // Reconstruct the successful maps into a, b vectors
        for (int i = 0; i < P_SIZE; ++i) {
            // If undefined, point to random in P (self loop or whatever) to keep valid
            if (a_map[i] == -1) a[i] = i; 
            else a[i] = a_map[i];
            
            if (b_map[i] == -1) b[i] = i;
            else b[i] = b_map[i];
        }
        
        // Determine u (state at step k)
        int u = 0;
        for (int i = 0; i < k; ++i) {
            if (S_known[i] == '0') u = a[u];
            else u = b[u];
        }
        
        // Setup branching at u
        // u is in P.
        // We want a[u] -> C0, b[u] -> C1.
        // Check availability
        // Since solve_mapping returned true, either a_map[u] == -1 or b_map[u] == -1 (or both).
        
        // We override a[u] and b[u] for the query.
        // Note: solve_mapping ensured we CAN override at least one without conflict.
        // If a_map[u] was defined, we MUST keep it?
        // Wait, solve_mapping used S_known to build constraints.
        // If a_map[u] is defined, it means u was visited with '0' in prefix.
        // So a[u] MUST be what it was.
        // But we want a[u] -> C0.
        // If a[u] is fixed to something in P, we CANNOT change it to C0.
        // Conflict!
        
        // Correction on logic:
        // We need u such that:
        // IF visited with '0', target is in C0. (This requires planning in prefix).
        // But prefix targets are in P.
        // So if u visited with '0', target is in P. We can't move it to C0.
        // So u MUST NOT have been visited with '0'.
        // Similarly, u MUST NOT have been visited with '1'.
        // So u must be a "virgin" state? Or at least clean for the branch we take?
        // We need to branch on S[k]. S[k] could be '0' or '1'.
        // We need a[u] != b[u] distinguishable.
        // If S[k] is '0', machine takes a[u].
        // If S[k] is '1', machine takes b[u].
        // We set a[u] -> C0, b[u] -> C1.
        // This requires a[u] not fixed to P, and b[u] not fixed to P.
        // So u must not be visited with '0' AND not visited with '1' in prefix.
        // i.e. u must NOT have been visited at all!
        // Wait. If u is visited, we arrive at u.
        // Previous step transition points TO u.
        // This is fine.
        // But FROM u, we must not have outgoing edges defined in prefix.
        // So u must be the LAST state of the path, and never appeared as an intermediate state (0..k-1).
        // So we need path p_0 ... p_k where p_k = u, and p_i != u for i < k.
        
        // Can we find such a path?
        // With P=90, length 1000.
        // Pigeonhole: we must reuse states.
        // So we cannot make u unique.
        // u MUST have been visited before.
        
        // Alternative:
        // Use the "Mixed Visits" strategy.
        // If u visited with '0' -> X, and '1' -> Y.
        // We need X != Y and X, Y distinguishable.
        // This means in the prefix construction, we must have ensured X != Y if both used.
        // AND we need X and Y to flow to distinguishable sinks.
        // If X, Y in P, they stay in P?
        // If we can make X flow to C0 and Y flow to C1 "eventually"?
        // But prefix keeps looping in P.
        
        // Revised Strategy:
        // We don't need a[u]->C0 immediately.
        // We just need a[u] and b[u] to eventually diverge to C0/C1.
        // But we don't know the suffix.
        // Suffix length decreases.
        // If we rely on random walk in P, likely they mix.
        
        // Let's go back to: We try to make u "clean" for one bit.
        // If u visited with '0', a[u] fixed to P. b[u] free.
        // Set b[u] -> C1.
        // a[u] stays in P.
        // If S[k] == '0', we stay in P.
        // If S[k] == '1', we go to C1.
        // Suffix behavior:
        // In C1: trap in C1.
        // In P: random walk?
        // If we stay in P, can we ensure we don't accidentally enter C1?
        // We control P transitions. We set them to stay in P.
        // So if S[k]=='0', result in P. If '1', result in C1.
        // Valid!
        // Requires: u NOT visited with '1'.
        // If u visited with '1', b[u] fixed to P.
        // Then we check if u visited with '0'.
        // If not, set a[u] -> C0.
        // Then '0' -> C0, '1' -> P. Distinguishable.
        // If u visited with BOTH, we fail.
        
        // So Condition is: u must NOT be visited with BOTH '0' and '1'.
        // This is much easier to satisfy!
        // In solve_mapping, we check this specific condition.
        
        // Updated solve_mapping logic inline here?
        // No, re-implement the loop with this check.
        
        // Retry loop
        int best_u = -1;
        bool found = false;
        
        // We use a simplified solver directly here
        static mt19937 rng(12345 + k);
        for (int attempt = 0; attempt < 5000; ++attempt) {
            fill(a_map.begin(), a_map.end(), -1);
            fill(b_map.begin(), b_map.end(), -1);
            int curr = 0;
            bool ok = true;
            for (int i = 0; i < k; ++i) {
                // record usage
                // curr is visited. outgoing edge determined by S[i].
                char c = S_known[i];
                int next_node;
                if (c == '0') {
                    if (a_map[curr] != -1) next_node = a_map[curr];
                    else { next_node = rng() % P_SIZE; a_map[curr] = next_node; }
                } else {
                    if (b_map[curr] != -1) next_node = b_map[curr];
                    else { next_node = rng() % P_SIZE; b_map[curr] = next_node; }
                }
                curr = next_node;
            }
            // curr is u.
            // Check if curr is clean for at least one bit
            // Clean '0': a_map[curr] == -1
            // Clean '1': b_map[curr] == -1
            if (a_map[curr] == -1 || b_map[curr] == -1) {
                // populate a and b
                for(int i=0; i<P_SIZE; ++i) {
                    a[i] = (a_map[i] == -1) ? i : a_map[i]; // default self loop or random
                    b[i] = (b_map[i] == -1) ? i : b_map[i];
                }
                
                u = curr;
                
                // Configure branching
                // C0: 90..94. C1: 95..99.
                // Setup C0/C1 internals (sinks)
                // Just map to themselves or cycle
                for(int i=C0_START; i<=C0_END; ++i) {
                    a[i] = b[i] = i; // simple sink
                }
                for(int i=C1_START; i<=C1_END; ++i) {
                    a[i] = b[i] = i;
                }
                
                // Branch at u
                // If a[u] free: set a[u] -> C0.
                // If b[u] free: set b[u] -> C1.
                // If both free: set both.
                // If one fixed (to P), the other goes to C/C1.
                // Result analysis:
                // If result in P -> fixed path taken.
                // If result in C0 -> '0' taken (via free edge).
                // If result in C1 -> '1' taken.
                
                if (a_map[u] == -1 && b_map[u] == -1) {
                    a[u] = C0_START;
                    b[u] = C1_START;
                } else if (a_map[u] == -1) {
                    // a free, b fixed to P
                    a[u] = C0_START;
                    // b[u] is already set to something in P
                } else {
                    // b free, a fixed to P
                    b[u] = C1_START;
                }
                
                found = true;
                break;
            }
        }
        
        if (!found) {
            // This is critical failure. 
            // In contest, maybe guess? Or try larger P?
            // With P=90, probability is very good.
            // Just use the last generated graph and hope? No, logic breaks.
            // We'll proceed with query and maybe get lucky or wrong answer.
            // Fallback: set a[u] -> C0, b[u] -> C1 anyway, overriding prefix.
            // This might make prefix path invalid, but maybe we land in u anyway?
            // (If we override, we change path for previous steps visiting u.
            // If u was visited at step j < k, and we change edge, path diverges.
            // Diverged path might not end at u. 
            // So we query something random.
            // But 5000 iters is a lot.)
        }
        
        // Execute Query
        int res = query(M, a, b);
        
        // Interpret Result
        // P range: 0..89
        // C0 range: 90..94
        // C1 range: 95..99
        
        if (res >= C0_START && res <= C0_END) {
            // Landed in C0.
            // This implies we took the branch to C0.
            // We only set edges to C0 from u.
            // Did we set a[u]->C0 or b[u]->C0?
            // We set a[u]->C0 (if free) or b[u]->C1 (if free).
            // We never set b[u]->C0.
            // So must be '0'.
            S_known += '0';
        } else if (res >= C1_START && res <= C1_END) {
            // Landed in C1. Must be '1'.
            S_known += '1';
        } else {
            // Landed in P.
            // Means we took the branch that stayed in P.
            // Which one was fixed to P?
            // If a[u] was free, we set it to C0.
            // If b[u] was free, we set it to C1.
            // If result in P, it means we took the path NOT set to C.
            // If a[u] -> C0 and b[u] -> P, and result in P, then '1'.
            // If a[u] -> P and b[u] -> C1, and result in P, then '0'.
            // Can check our config:
            bool a_to_C0 = (a[u] >= C0_START && a[u] <= C0_END);
            bool b_to_C1 = (b[u] >= C1_START && b[u] <= C1_END);
            
            if (a_to_C0) {
                // a went to C0. We are in P. So not '0'. Must be '1'.
                S_known += '1';
            } else {
                // b went to C1. We are in P. So not '1'. Must be '0'.
                S_known += '0';
            }
        }
    }
    
    guess(S_known);
    
    return 0;
}