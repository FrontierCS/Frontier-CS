#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>

using namespace std;

// Globals
int N, R;
struct Node {
    int id;
    int u, v; // Children indices
    bool u_is_gate;
    bool v_is_gate;
    char type; // '&' or '|', 0 if unknown
    int side_switch_val; // Value to enable path through this node (1 for &, 0 for |)
};

vector<Node> nodes;
vector<int> parent; // parent[i] = index of node that has i as child
vector<int> which_child; // 0 if left child (u), 1 if right (v)

// Map from switch index to node index (0..N-1)
// Switches 0..N-1 correspond to nodes 0..N-1
// Switches N..2N are leaves
int get_gate_id(int switch_idx) {
    if (switch_idx < N) return switch_idx;
    return -1;
}

// Current configuration of all switches
string current_switches;

// Function to query the judge
int query_judge(const string& s) {
    cout << "? " << s << endl;
    int res;
    cin >> res;
    return res;
}

// Helper to set ancestor switches to Enable path to a node
void set_ancestors_enable(int u) {
    int curr = u;
    while (curr != 0) {
        int p = parent[curr];
        int sibling_switch;
        if (which_child[curr] == 0) sibling_switch = nodes[p].v;
        else sibling_switch = nodes[p].u;
        
        // Sibling needs to output Enable value for p
        // sibling_switch output = slot_val(sibling) ^ s_sibling
        // We want output = nodes[p].side_switch_val
        // We can force this by setting s_sibling appropriately
        // BUT we don't know slot_val(sibling) if sibling is a gate
        // However, if sibling is a LEAF, slot_val is 0 (it's just a switch input, but handled as switch state). 
        // Wait, for leaves, the value is just the switch state.
        // For gates, we can control the switch at the output.
        // Regardless of gate output, we can toggle the switch to match desired value.
        // Wait, we don't know the gate output.
        // But for the recursive step, we assume we maintain the path sensitized.
        // Actually, we can just fix the switch state.
        // If we don't know the gate output, we can't guarantee the wire value.
        // BUT we processed top-down. We know the types of ancestors.
        // We do NOT know the outputs of gates that are off-path.
        // However, we can control the switch $s_{sibling}$. 
        // If sibling is a gate, its output is unknown.
        // This is a problem.
        // LUCKILY, for chains, the sibling is a LEAF.
        // For branching points, the sibling is a GATE.
        // When we are at a branching point, we just determined its type.
        // To go down to child 1, we need child 2 wire to be Enable.
        // Child 2 is a gate. We can set $s_{child2}$ to 0 or 1.
        // This gives wire value $X$ or $1-X$.
        // We don't know $X$.
        // But we can try both! One of them MUST work.
        // Since we process top-down, we can carry the correct setting.
        // When we solve a node, we find out which input combination passes.
        // Actually, simpler:
        // We only need to sensitize the path.
        // For a chain, side inputs are leaves, so we have full control.
        // For branching, we have few branches.
        // We can determine the "Enable" setting for the off-branch child immediately after determining the parent type.
        
        // This logic is handled in the main loop.
        
        curr = p;
    }
}

// We will maintain the 's' string globally and update it.
// Initially all '0'.

void solve() {
    if (cin >> N >> R) {} else return;
    nodes.resize(N);
    parent.assign(2 * N + 1, -1);
    which_child.assign(2 * N + 1, -1);
    
    for (int i = 0; i < N; ++i) {
        nodes[i].id = i;
        nodes[i].type = 0;
        cin >> nodes[i].u >> nodes[i].v;
        nodes[i].u_is_gate = (nodes[i].u < N);
        nodes[i].v_is_gate = (nodes[i].v < N);
        
        parent[nodes[i].u] = i;
        which_child[nodes[i].u] = 0;
        
        parent[nodes[i].v] = i;
        which_child[nodes[i].v] = 1;
    }
    
    current_switches = string(2 * N + 1, '0');
    
    // We need to know for each wire (output of switch i), what setting of s_i makes it 0 or 1?
    // Actually we only care about "forcing" a value.
    // For leaves (i >= N), setting s_i sets the value directly.
    // For gates (i < N), value is Gate_Out ^ s_i.
    // To force value V, we need s_i = Gate_Out ^ V.
    // We don't know Gate_Out. But we can toggle s_i to toggle value.
    
    // Set of active nodes (frontier)
    // We store pairs: (node_idx, s_value_to_toggle_input)
    // Actually, we just need to know the node index.
    // And we need to know the current switch settings that sensitize the path to it.
    // We maintain 'current_switches' such that paths to all nodes in 'frontier' are sensitized.
    // BUT different nodes might need different settings for common ancestors?
    // No, because they branch out. At the branching point, to see child A, we need child B to be Enable.
    // To see child B, we need child A to be Enable.
    // We can't see both simultaneously.
    // So 'frontier' is conceptually the set of nodes we want to solve, but we process them one by one or group by chain.
    
    // Let's implement the queue-based approach.
    vector<int> q;
    q.push_back(0);
    
    // For each node, we also need to know the "inversion" status of the path to root.
    // But we can detect it dynamically.
    
    // Since we can't visit all nodes in parallel due to branching conflicts,
    // we use a specific traversal.
    // We keep track of "known enable switch setting" for each wire found so far.
    // map<int, int> wire_enable_s; 
    // wire_enable_s[u] is the value of s_u that makes wire u "Enable" for its parent.
    // This is only needed for off-path branches.
    // For chains, off-path is leaf, so we just set leaf to 0 or 1.
    
    // Re-structure:
    // Recursive function solve_subtree(u).
    // Precondition: Path to u is sensitized. current_switches is set accordingly.
    // We also need to know if path inverts.
    // We can check path behavior by toggling 'main' input of u.
    // Main input comes from... children.
    // To check path, we can pick a leaf descendant L, and toggle L.
    // If root toggles, path is active.
    
    auto get_leaf_descendant = [&](int u) -> int {
        int curr = u;
        while (curr < N) {
            // Pick a child. Prefer gate child to follow main path, or just any.
            if (nodes[curr].u_is_gate) curr = nodes[curr].u;
            else if (nodes[curr].v_is_gate) curr = nodes[curr].v;
            else curr = nodes[curr].u; // Both leaves
        }
        return curr;
    };

    // Recursive solver
    // We pass the leaf that we use to wiggle.
    auto solve_recursive = [&](auto&& self, int u, int wiggler) -> void {
        // u is the current gate to solve.
        // wiggler is a leaf descendant of u, used to check signal propagation.
        
        // Check if u is start of a chain
        // A chain consists of nodes with exactly 1 gate child and 1 leaf child.
        // (If 2 leaves, it's a chain of 1).
        // (If 2 gates, it's a branch).
        
        vector<int> chain;
        vector<int> side_inputs; // Indices of side switches
        int curr = u;
        
        while (true) {
            chain.push_back(curr);
            int g_child = -1, l_child = -1;
            if (nodes[curr].u_is_gate) g_child = nodes[curr].u; else l_child = nodes[curr].u;
            if (nodes[curr].v_is_gate) {
                if (g_child != -1) { // Two gates -> Branching
                    // Current node is end of chain (it's the branching point)
                    // But we still need to solve it.
                    // It has no "side" input in terms of leaf. Both are gates.
                    // So chain stops BEFORE this node? Or this node is a singleton chain?
                    // We handle branching node separately.
                    // Remove from chain and break loop
                    chain.pop_back();
                    break;
                }
                g_child = nodes[curr].v;
            } else {
                if (l_child != -1) { // Two leaves
                    side_inputs.push_back(nodes[curr].v); // Arbitrary side
                    // Next is leaf, stop.
                    // But wait, if 2 leaves, we treat one as side, one as next?
                    // No, chain ends here.
                    break;
                }
                l_child = nodes[curr].v;
            }
            
            // Here we have 1 gate child, 1 leaf child.
            side_inputs.push_back(l_child);
            curr = g_child;
            if (curr == -1) break; // Should not happen given logic above
        }
        
        // Solve the chain
        if (!chain.empty()) {
            auto solve_range = [&](auto&& runner, int L, int R) -> void {
                if (L > R) return;
                
                // Try assuming all are AND
                // Set sides to 1
                for (int i = L; i <= R; ++i) {
                    current_switches[side_inputs[i]] = '1';
                }
                int base = query_judge(current_switches);
                // Toggle wiggler
                current_switches[wiggler] = (current_switches[wiggler] == '1' ? '0' : '1');
                int toggled = query_judge(current_switches);
                current_switches[wiggler] = (current_switches[wiggler] == '1' ? '0' : '1'); // Restore
                
                if (base != toggled) {
                    // All are AND
                    for (int i = L; i <= R; ++i) {
                        nodes[chain[i]].type = '&';
                        nodes[chain[i]].side_switch_val = 1; // AND needs 1 to enable
                    }
                    // Keep sides at 1 (Enable) for children
                    return;
                }
                
                // Try assuming all are OR
                for (int i = L; i <= R; ++i) {
                    current_switches[side_inputs[i]] = '0';
                }
                base = query_judge(current_switches);
                current_switches[wiggler] = (current_switches[wiggler] == '1' ? '0' : '1');
                toggled = query_judge(current_switches);
                current_switches[wiggler] = (current_switches[wiggler] == '1' ? '0' : '1');
                
                if (base != toggled) {
                    // All are OR
                    for (int i = L; i <= R; ++i) {
                        nodes[chain[i]].type = '|';
                        nodes[chain[i]].side_switch_val = 0; // OR needs 0 to enable
                    }
                    return;
                }
                
                // Mixed. Split.
                int mid = (L + R) / 2;
                // We need to pass signal through L..mid to test mid+1..R?
                // Or solve top part first.
                // Solving L..mid requires no knowledge of mid+1..R (except wiggling).
                // So solve L..mid first.
                // But if L..mid blocks, we can't test mid+1..R.
                // So we MUST determine L..mid types first.
                // Actually, the recursion should be: Find first blocking?
                // No, just split.
                runner(runner, L, mid);
                // After solving L..mid, their side switches are set to Enable.
                // So path to mid+1 is sensitized.
                runner(runner, mid + 1, R);
            };
            solve_range(solve_range, 0, chain.size() - 1);
        }
        
        // Now handle the node after the chain (curr)
        // If curr was branching (2 gate children)
        if (curr < N && nodes[curr].type == 0) { // Check if valid gate and not visited
            // It's a branching node or 2-leaf node that was skipped from chain?
            // If 2-leaf node, it was included in chain if logic above is correct?
            // Re-read chain logic:
            // "If 2 leaves ... side_inputs.push_back ... break".
            // So 2-leaf node IS in chain.
            // So curr must be a branching node (2 gates).
            
            // Solve curr (branching)
            // It has children u, v (both gates).
            // Wiggler is in one of the subtrees.
            // Say wiggler is under u.
            // To see wiggler, we need wire from v to be Enable.
            // Wire v value depends on $s_v$.
            // We can try $s_v=0$ and $s_v=1$. One will enable.
            // BUT we also need to determine type of curr.
            // We can determine type of curr using wiggler in u, AND varying wire v.
            
            // Procedure:
            // 1. Determine type of curr.
            //    Vary wire v ($s_v=0, 1$). Keep u active (wiggler).
            //    If curr is AND, need v=1 to pass.
            //    If curr is OR, need v=0 to pass.
            //    If we try $s_v=0$, and signal passes -> v=0 is Enable.
            //       If Enable is 0 -> Type OR.
            //       If Enable is 1 -> Type AND.
            //    So we just need to find which $s_v$ enables.
            //    Try $s_v=0$. Toggle wiggler.
            //    If passes -> Enable=0 -> Type=|. Record wire_enable_s[v] = 0.
            //    Else -> Enable=1 -> Type=&. Record wire_enable_s[v] = 1.
            //    (Assuming binary logic holds).
            
            int child_with_wiggler = -1, other_child = -1;
            // Determine which child has wiggler
            // Simple check: is wiggler in u's subtree?
            // We can just check wiggler index vs ranges if using DFS order, or just trace up.
            // Tracing up is O(depth).
            int temp = wiggler;
            while (temp != curr && temp != -1) temp = parent[temp];
            if (temp == curr) {
                // Determine direct child
                temp = wiggler;
                while (parent[temp] != curr) temp = parent[temp];
                if (temp == nodes[curr].u) {
                    child_with_wiggler = nodes[curr].u;
                    other_child = nodes[curr].v;
                } else {
                    child_with_wiggler = nodes[curr].v;
                    other_child = nodes[curr].u;
                }
            }
            
            // Try s_other = 0
            current_switches[other_child] = '0';
            int base = query_judge(current_switches);
            current_switches[wiggler] = (current_switches[wiggler] == '1' ? '0' : '1');
            int toggled = query_judge(current_switches);
            current_switches[wiggler] = (current_switches[wiggler] == '1' ? '0' : '1');
            
            if (base != toggled) {
                // Passed with s=0 -> Enable is 0 -> OR
                nodes[curr].type = '|';
                nodes[curr].side_switch_val = 0; // Not used as it's not a child
                // But for solving 'other_child', we need to keep 'child_with_wiggler' output at Enable (0).
                // We will handle recursion.
            } else {
                // blocked with s=0 -> Enable is 1 -> AND
                nodes[curr].type = '&';
                nodes[curr].side_switch_val = 1;
                // Set s_other = 1 to enable path for current session
                current_switches[other_child] = '1'; 
            }
            
            // Now recurse.
            // Path to child_with_wiggler is already sensitized (other_child set to Enable).
            self(self, child_with_wiggler, wiggler);
            
            // Now solve other_child.
            // Need to sensitize path to other_child.
            // This requires child_with_wiggler output to be Enable.
            // Enable val depends on nodes[curr].type.
            // If AND, need 1. If OR, need 0.
            // We can force child_with_wiggler wire to this value by setting s_{child_with_wiggler}.
            // But we don't know the output of gate child_with_wiggler.
            // Wait, we can assume it produces *something*, and we toggle s to flip it.
            // BUT we don't know the base value.
            // Trick: We can try s=0 and s=1.
            // One of them will allow signal from other_child to pass.
            // We need a wiggler for other_child.
            int other_wiggler = get_leaf_descendant(other_child);
            
            // Try s_{child_with_wiggler} = 0
            current_switches[child_with_wiggler] = '0';
            base = query_judge(current_switches);
            current_switches[other_wiggler] = (current_switches[other_wiggler] == '1' ? '0' : '1');
            toggled = query_judge(current_switches);
            current_switches[other_wiggler] = (current_switches[other_wiggler] == '1' ? '0' : '1');
            
            if (base == toggled) {
                // Blocked. Need s=1.
                current_switches[child_with_wiggler] = '1';
            }
            
            self(self, other_child, other_wiggler);
            
            // Restore? Not needed.
        }
        else if (curr < N) {
            // 2-leaf node, handled in chain logic?
            // If chain ended at 2-leaf node, it was solved.
            // If chain ended because branching...
            // Wait, the while loop for chain breaks if 2 gates.
            // If 2 leaves, it consumes the node into chain and breaks.
            // So if 2 leaves, type is already set.
            // If type set, just return.
            return;
        }
    };
    
    // Start recursion
    int root_wiggler = get_leaf_descendant(0);
    solve_recursive(solve_recursive, 0, root_wiggler);
    
    string ans = "";
    for (int i = 0; i < N; ++i) ans += nodes[i].type;
    cout << "! " << ans << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}