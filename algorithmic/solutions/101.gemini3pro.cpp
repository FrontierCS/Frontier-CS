#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <numeric>

using namespace std;

// Global state
int N, R;
struct Node {
    int id;
    int u, v; // inputs
    int p = -1; // parent
    char type = '?';
    int depth = 0;
};
vector<Node> nodes;
vector<int> current_s;
int current_output;

// Function to query the judge
int query() {
    string s = "";
    for (int i = 0; i < 2 * N + 1; ++i) {
        s += (current_s[i] ? '1' : '0');
    }
    cout << "? " << s << endl;
    int res;
    cin >> res;
    return res;
}

// Update a single switch and query
int query_flip(int idx) {
    current_s[idx] ^= 1;
    int res = query();
    // Restore state to avoid side effects? 
    // Usually we want to keep track of state. 
    // Here we update global state.
    current_output = res;
    return res;
}

// Just sets the array, doesn't query yet
void set_switch(int idx, int val) {
    current_s[idx] = val;
}

// Get output of a solved node given its inputs (from cache/logic)
// But we can't know outputs of internal nodes easily without simulation.
// We rely on sensitizing paths.

// Helper: For a known/leaf node `idx`, set its switch `S_idx` such that `Out_idx` becomes `val`.
// For leaf: Out = S. So set S = val.
// For solved internal: Out = (Val op S). We need Out = val. S = val ^ Val.
// But Val depends on inputs.
// Simpler: We just want to FORCE Out_idx to be `val`.
// We can do this if we control `S_idx`.
// If we know `Val_idx` (from children), we set `S_idx = val ^ Val_idx`.
// If we don't know `Val_idx`, we can't deterministically set `Out_idx`.
// BUT, for side inputs in our chain strategy, side inputs are either leaves or roots of solved subtrees.
// If leaf: trivial.
// If solved subtree: we can recursively set its output.
void force_output(int u, int target_val) {
    if (u >= N) {
        set_switch(u, target_val);
        return;
    }
    // Internal node u
    // We assume subtrees of u are already set to produce some value?
    // Actually, we maintain the invariant that "solved" subtrees are configured to produce a fixed value
    // or we compute it on the fly.
    // For the chain strategy, "side inputs" are just independent variables we can control.
    // We just need to know what S_u corresponds to Out_u = target.
    // We can compute current Val_u based on children configuration.
    int val_u = 0;
    // We need recursive computation?
    // Since we process top-down, and chains go down, side inputs are processed before?
    // No, side inputs are roots of subtrees. We solve recursively.
    // But to save queries, we don't query. We just compute using known types and current S.
    
    // Get values of children
    int val_left = -1, val_right = -1;
    // This requires children to be computed.
    // Recursion base case: leaves.
    auto get_val = [&](int child) -> int {
        if (child >= N) return current_s[child];
        // Recursive call? This might be expensive if deep.
        // But side inputs are roots of solved subtrees.
        // We can just simulate.
        return -1; // Placeholder
    };
    
    // Simulation function
    // We need to implement a full simulation of the current configuration for solved parts.
}

// Full simulation of the subtree rooted at u, returning its Output
// Assumes all gates in subtree are solved or are leaves.
int simulate(int u) {
    if (u >= N) return current_s[u];
    int v1 = simulate(nodes[u].u);
    int v2 = simulate(nodes[u].v);
    int gate_val = 0;
    if (nodes[u].type == '&') gate_val = min(v1, v2);
    else if (nodes[u].type == '|') gate_val = max(v1, v2);
    else {
        // Should not happen for solved subtree
        return 0;
    }
    return gate_val ^ current_s[u];
}

// Set switches in subtree u to produce target_val at u
void set_subtree_output(int u, int target_val) {
    if (u >= N) {
        current_s[u] = target_val;
        return;
    }
    // We can arbitrarily set children.
    // To make it simple, we just set children to (0,0) or (1,1) etc.
    // If we know type:
    // AND: need (1,1) for 1, any for 0.
    // OR: need (0,0) for 0, any for 1.
    // Strategy: Just set children to (0, 0).
    // Then AND -> 0, OR -> 0.
    // Then Val_u = 0.
    // Then Out_u = 0 ^ S_u. We want Out_u = target.
    // So S_u = target.
    // Recursively set children to 0.
    set_subtree_output(nodes[u].u, 0);
    set_subtree_output(nodes[u].v, 0);
    current_s[u] = target_val; 
    // Verification: Val_u = min/max(0,0) = 0. Out = 0^target = target. Correct.
}

void solve_branch(int u) {
    // Parent path is active.
    // Inputs L, R are unknown subtrees or leaves.
    // We treat them as black boxes. We control S_L, S_R.
    // Since L, R are NOT solved, we can't use simulate() or set_subtree_output().
    // But we can toggle S_L, S_R.
    // Regardless of Val_L, Val_R, toggling S_L flips Out_L.
    
    int L = nodes[u].u;
    int R = nodes[u].v;
    
    // We need 4 measurements relative to (S_L, S_R).
    // Base:
    int base = current_output;
    
    // Flip L
    current_s[L] ^= 1;
    int out_L = query();
    
    // Flip R
    current_s[L] ^= 1; // restore L
    current_s[R] ^= 1;
    int out_R = query();
    
    // Flip both
    current_s[L] ^= 1; // L flipped, R flipped
    int out_LR = query();
    
    // Restore
    current_s[L] ^= 1;
    current_s[R] ^= 1;
    current_output = base; // Should match query()
    
    // Analysis:
    // Let x = Out_L (base), y = Out_R (base).
    // Gate function g(x, y). Out_u = g(x, y) ^ S_u.
    // Global Out = Out_u ^ PathInv.
    // Let K = S_u ^ PathInv.
    // base = g(x, y) ^ K
    // out_L = g(!x, y) ^ K
    // out_R = g(x, !y) ^ K
    // out_LR = g(!x, !y) ^ K
    
    // Truth tables for g:
    // AND: 00->0, 01->0, 10->0, 11->1
    // OR:  00->0, 01->1, 10->1, 11->1
    
    // Sum of outputs (mod 2):
    // AND sum: 0+0+0+1 = 1 (odd)
    // OR sum: 0+1+1+1 = 1 (odd)
    // Both are odd. Sum doesn't distinguish.
    
    // But we know g is symmetric? Yes.
    // Let's check counts of 1s in (base, out_L, out_R, out_LR).
    // Let Z be the number of 1s.
    // If K=0:
    //   AND: three 0s, one 1. (Z=1)
    //   OR:  one 0, three 1s. (Z=3)
    // If K=1: (flip all bits)
    //   AND: three 1s, one 0. (Z=3)
    //   OR:  one 1, three 0s. (Z=1)
    
    // So if Z=1, it's (AND, K=0) OR (OR, K=1).
    // If Z=3, it's (OR, K=0) OR (AND, K=1).
    // Still ambiguous?
    // Wait. K = S_u ^ PathInv.
    // We know S_u. PathInv is unknown?
    // Actually, we can determine PathInv by looking at sensitization.
    // Sensitization means: does Out_u change Out_0?
    // We verified parent path is active. So Out_u DOES affect Out_0.
    // So PathInv is fixed constant (0 or 1).
    
    // Let's check sensitivity.
    // AND is sensitive to x only if y=1.
    // OR is sensitive to x only if y=0.
    
    // In our 4 queries, we have (y) and (!y).
    // One of them is the sensitizing value.
    // If g is AND:
    //   If y=1, flipping x changes output. (change seen between base <-> out_L)
    //   If y=0, flipping x does NOT change output. (no change base <-> out_L)
    //   So exactly one pair (base, out_L) or (out_R, out_LR) shows change.
    
    // Let's check change for L:
    bool change_L_base = (base != out_L);
    bool change_L_flipped = (out_R != out_LR);
    
    // For AND:
    //   Sensitive when other input is 1.
    //   Sensitive in base case => y=1.
    //   Sensitive in flipped case => !y=1 => y=0.
    //   So exactly one of change_L_base/change_L_flipped is true.
    // For OR:
    //   Sensitive when other input is 0.
    //   Sensitive in base case => y=0.
    //   Sensitive in flipped case => !y=0 => y=1.
    //   Exactly one is true.
    
    // This just confirms active path, doesn't distinguish AND/OR.
    
    // We need to correlate with sensitivity to R.
    bool change_R_base = (base != out_R);
    // For AND:
    //   Sensitive to R if x=1.
    //   Sensitive to L if y=1.
    //   If base is (1, 1), both sensitive.
    //   If base is (0, 0), neither sensitive.
    //   If (0, 1), L sensitive, R not.
    //   If (1, 0), L not, R sensitive.
    
    // Let's count how many sensitivities in base config:
    int sens = 0;
    if (change_L_base) sens++;
    if (change_R_base) sens++;
    
    if (sens == 2) {
        // Both sensitive. Must be (1, 1).
        // AND(1, 1) = 1. OR(1, 1) = 1.
        // Can't distinguish?
        // Wait, if inputs are (1, 1):
        // AND -> 1. OR -> 1.
        // If we change to (0, 0) (flip both):
        // AND -> 0. OR -> 0.
        // Output changes.
        // This means we are at (1, 1).
        // BUT we need to know if (0, 1) produces 0 or 1.
        // Check out_L (inputs 0, 1).
        // If AND: 0. Change from base(1) seen. (Confirmed by sens).
        // If OR: 1. No change from base(1).
        // So:
        // If sens == 2:
        //   Check change_L_base.
        //   If true (output changed), then value changed 1->0.
        //   This implies AND. (1->0 is change).
        //   Wait, for OR: (1, 1)->1, (0, 1)->1. No change.
        //   So if change_L_base is true, it MUST be AND.
        //   If change_L_base is false, it MUST be OR?
        //   But we said sens=2, so change_L_base IS true.
        //   Contradiction?
        //   For OR with (1, 1):
        //     L flips -> (0, 1) -> 1. No change.
        //     So change_L_base would be FALSE.
        //   So sens cannot be 2 for OR at (1, 1).
        //   Thus, if sens == 2, it is AND.
        nodes[u].type = '&';
        // And we know base inputs are (1, 1).
        // We need to sensitize L and R.
        // For AND, need 1.
        // S_L, S_R are already correct (since base is 1, 1).
    } else if (sens == 0) {
        // Neither sensitive. Must be (0, 0).
        // AND(0, 0) = 0. OR(0, 0) = 0.
        // Check out_L (1, 0).
        // AND: 0. No change.
        // OR: 1. Change.
        // But sens=0 means change_L_base is false.
        // So out_L == base.
        // This implies AND (0->0).
        // If it were OR (0->1), it would change.
        // So sens=0 implies AND.
        // Wait, check OR logic again.
        // OR at (0, 0). Flip L -> (1, 0) -> 1. Change!
        // So for OR at (0, 0), sens would be at least 1 (L sensitive).
        // Actually, if sens=0, it means L flip -> no change, R flip -> no change.
        // For AND at (0, 0): L flip->(1,0)->0 (no change). R flip->(0,1)->0 (no change).
        // So sens=0 => AND at (0, 0).
        nodes[u].type = '&';
        // Base inputs (0, 0).
        // To sensitize L (need 1), we must flip S_R.
        // To sensitize R (need 1), we must flip S_L.
        // So flip both S_L and S_R in global state.
        query_flip(L); 
        query_flip(R);
    } else {
        // sens == 1.
        // Inputs are (0, 1) or (1, 0).
        // Assume (0, 1). L=0, R=1.
        // AND(0, 1) = 0. Sensitive to L? (1, 1)->1 (Change). Yes.
        //                Sensitive to R? (0, 0)->0 (No Change). No.
        // So AND at (0, 1) has L-sensitive, R-not.
        // OR at (0, 1) = 1. Sensitive to L? (1, 1)->1 (No Change). No.
        //               Sensitive to R? (0, 0)->0 (Change). Yes.
        // So if (0, 1): AND -> L sens. OR -> R sens.
        // Distinct!
        
        // Assume (1, 0). L=1, R=0.
        // AND(1, 0) = 0. L sens? (0, 0)->0 (No). No.
        //                R sens? (1, 1)->1 (Yes). Yes.
        // OR(1, 0) = 1. L sens? (0, 0)->0 (Yes). Yes.
        //               R sens? (1, 1)->1 (No). No.
        
        // Summary for sens=1:
        // L sensitive, R not: AND(0,1) or OR(1,0).
        // L not, R sensitive: AND(1,0) or OR(0,1).
        
        // We have ambiguity.
        // AND(0,1) vs OR(1,0).
        // Outputs: AND->0. OR->1.
        // If we knew PathInv, we could distinguish.
        // But we don't.
        // Can we check out_LR? (Flip both).
        // (0, 1) -> (1, 0).
        // AND: 0 -> 0. (No change).
        // OR: 1 -> 1. (No change).
        // Doesn't help.
        
        // We need another state.
        // We tried (x, y), (!x, y), (x, !y), (!x, !y).
        // We have all 4 states.
        // AND produces 1 three times? No, 0 three times, 1 once.
        // OR produces 1 three times, 0 once.
        // So just count the number of 1s (or 0s) in the 4 outputs?
        // Z = count(outputs == 1).
        // If PathInv=0:
        //   AND outputs (0,0,0,1). Z=1.
        //   OR outputs (0,1,1,1). Z=3.
        // If PathInv=1:
        //   AND outputs (1,1,1,0). Z=3.
        //   OR outputs (1,0,0,0). Z=1.
        
        // So if Z=1 => (AND, Inv=0) or (OR, Inv=1).
        //    if Z=3 => (OR, Inv=0) or (AND, Inv=1).
        // Still coupled.
        
        // WAIT.
        // We assume we don't know PathInv.
        // But for sens=1 case:
        // L sensitive means changing L flips output.
        // So PathInv is effectively observed between L and Root.
        // No.
        
        // Let's look at the sensitivities again.
        // Case A: L sens, R not.
        //   Possibilities: AND(0,1) or OR(1,0).
        //   AND(0,1) -> 0. Change L -> 1. (Flip).
        //   OR(1,0) -> 1. Change L -> 0. (Flip).
        //   In both cases, changing L flips output.
        //   But sensitizing R:
        //   AND(0,1): Need R=1. R is 1. Already sensitized.
        //   OR(1,0): Need R=0. R is 0. Already sensitized.
        //   So regardless of type, R is sensitized!
        //   What about L?
        //   AND(0,1): Need L=1. L is 0. Need flip S_L.
        //   OR(1,0): Need L=0. L is 1. Need flip S_L.
        //   Wait. If L=0, S_L makes it 0. To get 1, flip S_L.
        //   If L=1, S_L makes it 1. To get 0, flip S_L.
        //   In both cases, we need to flip S_L to sensitize L.
        //   So ACTION is same!
        //   We don't know type, but we know how to sensitize children!
        //   For R: Keep S_R. For L: Flip S_L.
        //   Wait, does this work?
        //   If we don't know type, can we solve children?
        //   We need to know type for FINAL answer.
        //   But maybe we can deduce type LATER?
        //   Or maybe we can distinguish now?
        //   AND(0,1) output 0. OR(1,0) output 1.
        //   If we knew PathInv...
        
        // Can we determine PathInv?
        // We know parent is active.
        // If parent was AND: we set u to 1.
        // If u outputs 1, PathInv is determined by parent's PathInv.
        // We know parent's PathInv (recursively).
        // So yes, we know PathInv!
        
        // Let's track expected PathInv.
        // Root: PathInv = 0.
        // When going down:
        // If Parent is AND: we forced sibling to 1. Parent passes signal. Inversion = ParentInversion.
        // If Parent is OR: we forced sibling to 0. Parent passes signal. Inversion = ParentInversion.
        // Wait, does S_parent affect Inversion?
        // Out_parent = (Out_u op side) ^ S_parent.
        // If S_parent=1, it inverts.
        // So Inversion accumulates S along the path.
        // Yes! We know all S along the path.
        // So we know PathInv.
        
        // Algorithm update:
        // Track `current_path_inv` (from u to root).
        // Base case: Root inv = 0.
        // When solving u:
        //   Calculate observed output at u: Out_u = current_output ^ current_path_inv.
        //   Now we know Out_u (0 or 1).
        //   Z counts (Out_u for the 4 cases).
        //   AND(0001), OR(0111).
        //   Z=1 => AND. Z=3 => OR.
        //   Solved!
        
        int Z = 0;
        int path_inv = 0; // passed as argument or maintained
        // To maintain path_inv, we need to pass it.
        // But global state change?
        // Better: calculate it.
        // Since we fix S along path, we can store it.
        // Or maintain in DFS.
        // Re-calculate Z using current_path_inv.
        
        // We need to implement passing path_inv.
    }
}

// Global recursion
void solve(int u, int path_inv);

void solve(int u, int path_inv) {
    // If u is leaf, done.
    if (u >= N) return;
    
    // Determine Type of u
    int L = nodes[u].u;
    int R = nodes[u].v;
    
    // We assume u's path to root is active with inversion `path_inv`.
    // We perform 4 queries to find type and inputs.
    
    int results[4];
    int sL_orig = current_s[L];
    int sR_orig = current_s[R];
    
    // 00
    results[0] = query(); // current state
    // 01
    current_s[R] ^= 1;
    results[1] = query();
    // 11
    current_s[L] ^= 1;
    results[3] = query();
    // 10
    current_s[R] ^= 1;
    results[2] = query();
    
    // Restore
    current_s[L] ^= 1; 
    // Now at 00 (original)
    
    // Map to node output
    int node_outs[4];
    int ones = 0;
    for(int i=0; i<4; ++i) {
        node_outs[i] = results[i] ^ path_inv;
        if(node_outs[i]) ones++;
    }
    
    // Decide type
    if (ones == 1) nodes[u].type = '&';
    else nodes[u].type = '|';
    
    // Determine which config corresponds to (1, 1) [for AND] or (0, 0) [for OR].
    // AND: (1, 1) is the unique 1.
    // OR: (0, 0) is the unique 0.
    
    int unique_idx = -1;
    if (nodes[u].type == '&') {
        for(int i=0; i<4; ++i) if(node_outs[i] == 1) unique_idx = i;
    } else {
        for(int i=0; i<4; ++i) if(node_outs[i] == 0) unique_idx = i;
    }
    
    // unique_idx is the index in (00, 01, 10, 11) relative to STARTING S_L, S_R.
    // 0: no flip. 1: R flip. 2: L flip. 3: Both flip. (Based on traversal order 0->1->3->2)
    // My order: 0(00) -> 1(01) -> 3(11) -> 2(10).
    // indices: 0, 1, 3, 2.
    // Wait, array index:
    // results[0]: 00
    // results[1]: 01
    // results[3]: 11
    // results[2]: 10
    
    // We want to set inputs to sensitize children.
    // If AND: need (1, 1). This is config unique_idx.
    // If OR: need (0, 0). This is config unique_idx.
    // So we apply the flips dictated by unique_idx.
    
    if (unique_idx == 1) { // 01: flip R
        current_s[R] ^= 1;
    } else if (unique_idx == 2) { // 10: flip L
        current_s[L] ^= 1;
    } else if (unique_idx == 3) { // 11: flip both
        current_s[L] ^= 1;
        current_s[R] ^= 1;
    }
    // if 0: do nothing.
    
    // Now inputs are set to identity.
    // Path inv for children:
    // Out_u = (L op R) ^ S_u.
    // If we vary L (holding R constant identity):
    // AND: Out_u = (L & 1) ^ S_u = L ^ S_u.
    // OR:  Out_u = (L | 0) ^ S_u = L ^ S_u.
    // So inversion adds S_u.
    // Updated path_inv = path_inv ^ current_s[u].
    
    int next_inv = path_inv ^ current_s[u];
    
    solve(L, next_inv);
    solve(R, next_inv);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N >> R;
    nodes.resize(2 * N + 1);
    for (int i = 0; i < 2 * N + 1; ++i) nodes[i].id = i;
    
    // Input format: N lines Ui Vi.
    // Correspond to gates 0..N-1?
    // Sample:
    // 3 2
    // 3 4
    // 2 4
    // 0 1
    // Problem description: "For i = N-1, N-2, ..., 0 ... Slot i is connected to Ui, Vi".
    // So the input lines are for N-1, N-2 ... 0.
    // We should store them correctly.
    
    vector<pair<int, int>> connections(N);
    for (int i = 0; i < N; ++i) {
        cin >> connections[i].first >> connections[i].second;
    }
    // Assign to nodes N-1 down to 0
    for (int i = 0; i < N; ++i) {
        int u = connections[i].first;
        int v = connections[i].second;
        int gate_idx = N - 1 - i;
        nodes[gate_idx].u = u;
        nodes[gate_idx].v = v;
        nodes[u].p = gate_idx;
        nodes[v].p = gate_idx;
    }
    
    // Initial state
    current_s.assign(2 * N + 1, 0);
    // Initial query to get baseline
    current_output = query();
    
    // Start solving from root 0. path_inv = 0.
    solve(0, 0);
    
    // Output result
    string res = "";
    for (int i = 0; i < N; ++i) {
        res += nodes[i].type;
    }
    cout << "! " << res << endl;
    
    return 0;
}