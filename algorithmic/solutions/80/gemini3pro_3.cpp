#include <iostream>
#include <vector>
#include <string>
#include <cstdlib>
#include <ctime>

using namespace std;

int M;
int N_found = 0;
int adj[25][25];
int stone_logical[25]; // tracks logical index of stone. 0 initially.
// We maintain invariant: for all known nodes, stone is at logical 0, side "left".
// Exception: u during exploration is marked "right". Candidates during ID are marked "right".

// Path helper
struct Path {
    vector<int> edges;
};

// BFS to find path from src to dst in known graph
vector<int> get_path(int src, int dst) {
    if (src == dst) return {};
    vector<int> q;
    q.push_back(src);
    vector<int> parent(25, -1);
    vector<int> edge_from(25, -1);
    vector<bool> vis(25, false);
    vis[src] = true;
    
    int head = 0;
    while(head < q.size()){
        int u = q[head++];
        if (u == dst) break;
        for(int i=0; i<M; ++i){
            int v = adj[u][i];
            if (v != -1 && !vis[v]){
                vis[v] = true;
                parent[v] = u;
                edge_from[v] = i;
                q.push_back(v);
            }
        }
    }
    
    vector<int> path;
    int curr = dst;
    while(curr != src){
        path.push_back(edge_from[curr]);
        curr = parent[curr];
    }
    // reverse
    vector<int> res;
    for(int i=path.size()-1; i>=0; --i) res.push_back(path[i]);
    return res;
}

// Interaction functions
string query(int stone_move, string side, int take_passage) {
    cout << stone_move << " " << side << " " << take_passage << endl;
    string resp;
    cin >> resp;
    if (resp == "treasure") exit(0);
    return resp;
}

// Helper to align stone and take passage
// Current node u. We want to take logical edge p_idx.
// We move stone to logical p_idx Left, then take 0 relative to it.
string take_logical_edge(int u, int p_idx) {
    int current_s = stone_logical[u];
    int target_s = p_idx;
    int move_val = (target_s - current_s + M) % M;
    stone_logical[u] = target_s; // update state
    return query(move_val, "left", 0);
}

// Helper to just change stone side at current node u (logical 0)
// Warning: this assumes we are at u and stone is at logical 0 Left/Right.
void set_stone_side(int u, string side) {
    // We assume stone is at correct position, just changing side.
    // Move 0 steps.
    // However, we must take a passage.
    // This is problematic. We cannot change stone without moving.
    // So "Marking" implies moving.
    // We only use marking when we move away.
    // To "Unmark" c, we go to c, set side, and leave.
}

// We need a robust "Go to Right" function
// Returns nothing, but ensures we are at a node with Stone "Right".
string random_walk_until_right() {
    string s;
    // We don't know where we are, so logical tracking is impossible?
    // Actually, "center" implies new node, "left"/"right" implies old.
    // If we are lost, we just output 0 left 0 (random walk).
    // But we need to be careful not to mess up logical stones of known nodes.
    // Known nodes have stone at logical 0.
    // If we output 0 left 0, we keep stone at 0.
    // So we don't disrupt the map.
    while(true) {
        // Read current state is not possible without moving? 
        // No, the system outputs state after previous move.
        // We assume we just arrived and saw `s`.
        // But this function is called when we need to find u.
        // We need to pass the last seen state?
        // Let's assume the caller handles the first check.
        // We iterate: output move, read state.
        
        // This function is tricky because we need the LAST state.
        // Let's integrate it in the flow.
        break; 
    }
    return "";
}

// Global state for last read response
string last_resp;

void walk_to_right() {
    while (last_resp != "right") {
        // Random walk
        // Keep stone at logical 0 (move 0 left), take random passage
        int r = rand() % M;
        last_resp = query(0, "left", r);
        if (last_resp == "center") {
            // Unexpected new node during random walk?
            // Should not happen if we only walk in known graph.
            // But if it happens, we treat it as part of the graph?
            // For now, assume closed world during ID.
        }
    }
}

// Function to traverse a specific path of edge indices
// updates last_resp
void traverse_path(const vector<int>& p) {
    for (int edge : p) {
        // We are at some node. We assume stone is at 0 left.
        // We want to take logical edge `edge`.
        // move stone to `edge` left.
        // take 0.
        // Since we don't know node ID, we can't track `stone_logical`.
        // BUT, for known nodes, we enforce `stone_logical` is 0.
        // So `current_s` is 0.
        // `move_val` = edge.
        last_resp = query(edge, "left", 0);
        
        // After move, stone is at `edge`.
        // We need to reset it to 0 for the invariant.
        // But we are at a new node now.
        // The stone at the PREVIOUS node is left at `edge`.
        // This breaks invariant!
        // We must ensure stone is at 0 before leaving?
        // Or we allow stone to be anywhere?
        // If we allow anywhere, we need to know where it is when we return.
        // Simplified: Always reset stone to 0 before leaving?
        // Can't. "Place stone ... and take passage". Atomic.
        
        // Solution: When we define logical 0, we stick to it.
        // If we leave stone at `edge`, then `stone_logical` for that node becomes `edge`.
        // We need to track `stone_logical` for all nodes.
        // During identification, we might lose track of which node is which.
        // This is the main issue.
        
        // Alternate invariant: Stone is always at logical 0.
        // To take edge `k`, we output `k left k`.
        // "move stone k clockwise (to k), take passage k clockwise relative to OLD (k)".
        // Wait. "Both numbers are relative to the passage marked by the stone".
        // Marked by stone BEFORE move? No.
        // Example: "3 left 1". 
        // Moves stone +3. Places it.
        // Takes passage +1 relative to OLD stone pos.
        // So if stone at 0. Move +3 -> Stone at 3.
        // Take +1 -> Passage 1.
        // Stone ends up at 3.
        // Passage taken is 1.
        // We want passage `k`, stone back at 0?
        // To have stone at 0, we need `move` s.t. `(0 + move) % M == 0` => `move = 0`.
        // So we must output `0 ...`. Stone stays at 0.
        // Then we take passage relative to 0. i.e., `k`.
        // Output `0 left k`.
        // Stone stays at 0. Passage k taken.
        // Perfect.
        // So we don't need `stone_logical` array if we always do `0 left k`.
        // Stone always stays at 0.
        // Invariant holds.
    }
}

// To mark a node Right:
// We are at node X. Stone is at 0 Left.
// We want Stone at 0 Right. Move away?
// We need to exit.
// Output `0 right k`. Stone becomes 0 Right. We take passage k.
// X is now marked Right.

void identify_and_resolve(int u, int p_from_u);

// Global
int total_nodes = 0;

void DFS(int u) {
    for (int i = 0; i < M; ++i) {
        if (adj[u][i] == -1) {
            // Explore u -> i
            // Mark u as Right
            // Output `0 right i`. Stone at u becomes Right. We take edge i.
            last_resp = query(0, "right", i);
            
            if (last_resp == "center") {
                // New node
                int v = total_nodes++;
                adj[u][i] = v;
                // Initialize v
                // v's stone is Center.
                // We define passage 0 as the one we take with `0 left 0`.
                // Stone becomes 0 Left.
                // We take edge 0.
                last_resp = query(0, "left", 0);
                // Now we are at w = adj[v][0].
                // We are recursively deep.
                // We need to handle this edge v->0 first.
                // This logic is getting messy.
                // Let's adopt a "Iterative" approach or manage stack manually?
                // Or simply:
                // We are at w.
                // We treat this as if we just arrived at w from v via 0.
                // Call a helper function `HandleArrival(from, edge)`.
                
                // But first we must unmark u!
                // u is Right. v is Left (now).
                // We can use RW to find u.
                walk_to_right(); // Finds u
                // At u (Right). Set Left.
                // But we need to traverse back to v, then w.
                // We know u->v is edge i. v->w is edge 0.
                // To set u Left: `0 left i`.
                // Stone at u becomes Left. We take edge i -> v.
                last_resp = query(0, "left", i);
                // At v. Take edge 0 -> w.
                // `0 left 0`. Stone at v stays Left (already Left).
                last_resp = query(0, "left", 0);
                
                // Now at w.
                // Recursively solve from v's perspective.
                // We need to execute DFS(v).
                // But we are already at w (v's 0-th neighbor).
                // So inside DFS(v), we skip edge 0 exploration and handle w.
                
                // To simplify:
                // We call `process_edge_result(v, 0)`.
                // Then loop 1..M-1.
                
                // Let's formalize process_edge(u, i):
                // Assumes we are at u.
                // checks adj[u][i]. If -1, explores.
            } else if (last_resp == "right") {
                // v == u
                adj[u][i] = u;
                // At u (Right).
                // Set Left. Stay at u? No, we must take passage.
                // We are done with this edge.
                // Just random move to self?
                // We can take edge `i` again? Or any known edge.
                // We want to stay at u to continue loop.
                // But we must move.
                // If we take edge `i` again (which is u->u), we land at u.
                // So `0 left i`.
                last_resp = query(0, "left", i);
                // At u.
            } else {
                // Left. Old node v != u.
                // Identify v.
                int v = -1;
                // Candidates
                vector<int> candidates;
                for(int k=0; k<total_nodes; ++k) if(k != u) candidates.push_back(k);
                
                // Binary search or linear scan?
                // Linear scan with robustness.
                for (int c : candidates) {
                    // Check if v == c.
                    // u is Right. v is Left.
                    // We are at v.
                    
                    // 1. Go to u.
                    walk_to_right(); 
                    // At u.
                    
                    // 2. Mark c Right.
                    // Path u->c.
                    vector<int> p = get_path(u, c);
                    traverse_path(p); 
                    // At c. Mark Right.
                    // Use loop back to u? or just set Right and leave?
                    // We need to return to u.
                    // Since u is Right, RW works.
                    // `0 right 0` (dummy edge 0).
                    last_resp = query(0, "right", 0); // c becomes Right. Move to adj[c][0].
                    
                    // 3. Return to u.
                    walk_to_right();
                    // At u.
                    
                    // 4. Go u -> v.
                    // Edge i.
                    // `0 right i`. (Keep u Right).
                    last_resp = query(0, "right", i);
                    
                    // 5. Check v.
                    if (last_resp == "right") {
                        v = c;
                        // Found.
                        // v is Right.
                        // Set v Left.
                        // `0 left 0` -> random.
                        last_resp = query(0, "left", 0);
                        // RW to u.
                        walk_to_right();
                        // At u.
                        break;
                    } else {
                        // v != c.
                        // Unmark c.
                        // RW to Right (finds u or c).
                        while(true) {
                            walk_to_right();
                            // We are at z (Right).
                            // Is z == u or z == c?
                            // Try path u->c.
                            // If we are at u, we reach c (Right).
                            // If we are at c, we reach ???
                            
                            // Let's try to set Left.
                            // If we are at c, setting Left cleans c. u remains Right. Good.
                            // If we are at u, setting Left cleans u. c remains Right. Bad.
                            // We want u Right, c Left.
                            
                            // Heuristic:
                            // Assume we are at u.
                            // traverse u->c.
                            p = get_path(u, c);
                            traverse_path(p);
                            // If we see Right, we were at u, reached c.
                            if (last_resp == "right") {
                                // Set c Left.
                                last_resp = query(0, "left", 0);
                                // Done unmarking.
                                break; 
                            } else {
                                // We were at c? Or path leads to Left.
                                // If we were at c, u->c path moves us away.
                                // c is still Right. u is Right.
                                // Continue loop.
                            }
                        }
                        
                        // Ensure we are back at u.
                        walk_to_right();
                    }
                }
                
                adj[u][i] = v;
                // At u (Right).
                // Set u Left.
                // `0 left 0`.
                last_resp = query(0, "left", 0);
                // We moved to random neighbor.
                // Go back to u.
                p = get_path(adj[u][0], u); // Wait, we took edge 0.
                // We know where we are? Yes, adj[u][0].
                // If adj[u][0] unknown, we are in trouble.
                // But we iterate edges in order?
                // If i > 0, then 0 is known.
                // If i == 0, we took edge 0. adj[u][0] is v.
                // So we know where we are.
                int curr = adj[u][0];
                p = get_path(curr, u);
                traverse_path(p);
                // At u.
            }
        }
    }
}

// We need a proper recursive structure that handles the "arrival at w" case.
// But standard DFS is easier if we can just "teleport" back to u.
// With `get_path` and SC property, we can navigate.

void solve_dfs(int u) {
    for (int i = 0; i < M; ++i) {
        if (adj[u][i] == -1) {
            // Explore
            // Mark u Right
            last_resp = query(0, "right", i);
            
            if (last_resp == "center") {
                int v = total_nodes++;
                adj[u][i] = v;
                // Initialize v
                // Stone is Center.
                // Output `0 left 0`.
                last_resp = query(0, "left", 0);
                
                // We are now at w = adj[v][0].
                // We need to handle this.
                // This is effectively exploring v->0.
                
                // Unmark u logic:
                // We need to unmark u eventually.
                // But now we are deep.
                // Let's just track that u is Right.
                // Recursion will handle w.
                // We need to pass `v` and `0` to recursive step.
                
                // Actually, simply:
                // We are at w.
                // We need to resolve w.
                // Call a function `resolve_arrival(from_v, edge_0)`.
                // Then continue DFS on v.
                
                // To do this cleanly:
                // We need to unmark u first to keep things sane?
                // Yes.
                
                walk_to_right(); // Find u
                // At u. Set Left. Go back to v.
                // `0 left i`.
                last_resp = query(0, "left", i);
                // At v. Take edge 0.
                // `0 left 0`.
                last_resp = query(0, "left", 0);
                
                // Now at w. u is Left. v is Left.
                // Recursively solve.
                // We are "mid-edge".
                // We need `process_edge(v, 0)`.
                // But we are ALREADY moved.
                // We need a version of DFS that starts AFTER move.
                
                process_arrival(v, 0);
                
                // Continue v's other edges
                solve_dfs(v);
                
                // Return to u
                vector<int> p = get_path(v, u);
                traverse_path(p);
            } 
            else if (last_resp == "right") {
                adj[u][i] = u;
                // At u. Set Left.
                // Take any known edge to stay safe or stay at u.
                // If we take i (u->u), we stay at u.
                last_resp = query(0, "left", i);
            } 
            else {
                // Left. Old node.
                int v_found = -1;
                vector<int> cands;
                for(int k=0; k<total_nodes; ++k) if(k!=u) cands.push_back(k);
                
                for(int c : cands) {
                    walk_to_right(); // Find u
                    // Mark c Right
                    vector<int> p = get_path(u, c);
                    traverse_path(p);
                    last_resp = query(0, "right", 0); // c Right, move to adj[c][0]
                    
                    walk_to_right(); // Find u
                    last_resp = query(0, "right", i); // u Right, move to v
                    
                    if (last_resp == "right") {
                        v_found = c;
                        last_resp = query(0, "left", 0); // v Left
                        walk_to_right(); // Find u
                        break;
                    } else {
                        // Unmark c
                         while(true) {
                            walk_to_right();
                            // z is Right.
                            vector<int> p2 = get_path(u, c); // Try path u->c
                            traverse_path(p2);
                            if (last_resp == "right") {
                                // We reached c
                                last_resp = query(0, "left", 0);
                                break;
                            }
                        }
                        walk_to_right(); // Find u
                    }
                }
                adj[u][i] = v_found;
                // At u. Set Left.
                // We need to move.
                // Take edge i (u->v).
                last_resp = query(0, "left", i);
                // At v. Go back to u.
                vector<int> p = get_path(v_found, u);
                traverse_path(p);
            }
        }
    }
}

void process_arrival(int u, int i) {
    // We just took edge i from u and landed at current node.
    // Determine what current node is.
    if (last_resp == "center") {
        int v = total_nodes++;
        adj[u][i] = v;
        last_resp = query(0, "left", 0);
        // At w = adj[v][0]
        process_arrival(v, 0);
        solve_dfs(v);
        // Return to u? No, we are done with branch v.
        // But we need to be at v to return to u?
        // process_arrival expects us to be at result of u->i.
        // Wait, solve_dfs(v) ends at v.
        // So we are at v.
        // We need to go back to u?
        // No, process_arrival is just updating adj[u][i].
        // The caller of process_arrival expects to be at v?
        // No, caller logic handles return.
    } else if (last_resp == "right") {
        // Should not happen if all Left.
        // But logic is same as DFS.
        // Since we didn't mark u Right before calling process_arrival (because we came from recursion),
        // we can't distinguish u easily?
        // Ah. The "New Node" path comes from `query(0, "left", 0)`.
        // Stones are all Left.
        // So u is Left.
        // If we hit Right, it's impossible.
        // If we hit Left, it's an old node.
        // But which one?
        // We need to identify.
        // To identify, we need to mark u Right.
        // But we are at v. We need to go back to u to mark it.
        // We know u->v is edge i.
        // But we don't know v.
        // And we can't find u (all Left).
        
        // ISSUE: Recursive step `query(0, "left", 0)` landing at old node.
        // We are at unknown v. u is known. Edge u->v is 0.
        // All stones Left.
        // We can't find u.
        // BUT v is a neighbor of u.
        // If v is Old, it is in Known set.
        // Can we iterate all nodes k, check if k->0 leads to v?
        // Yes!
        // For each candidate c:
        //   Check if u->0 leads to c.
        //   How?
        //   Mark c Right.
        //   Go to u.
        //   Take edge 0.
        //   Check.
        //   Problem: How to go to u?
        //   We are at v. All stones Left.
        //   We are lost.
        //   However, graph is small.
        //   RW will hit some node.
        //   We can try to "Home" to node 0?
        //   Sequence to node 0?
        //   If we can identify ANY node, we can go to u.
        
        // This suggests we should always maintain a marked "Home" node?
        // Or root is always Right?
        // If root is always Right, we can find root.
        
        // Let's restart with invariant: Node 0 is ALWAYS Right.
        // All others Left.
        // When ID needed:
        //   If u != 0:
        //     Go to 0.
        //     Navigate to u.
        //     Mark u Right (offset 1? No).
        //     Just use 0 as base.
        
        // Actually, simpler:
        // Just rely on "Assume we are at k", execute path to u, check.
        // Probabilistic homing.
        // At unknown v:
        //   Guess we are at k.
        //   Path k->root.
        //   Check if we hit root? (Root is 0).
        //   To verify root: Mark root Right?
        //   If we keep 0 Right always.
        //   Then hitting Right means we hit 0.
        //   So:
        //   Loop k in Known:
        //     Assume v=k.
        //     Path k->0.
        //     If hit Right -> Verified (likely).
        //     Then v=k.
        //     Nav back to u.
        //   This is nice.
        
        // Invariant: Node 0 always Right.
        // All others Left.
        // New nodes Center -> set Left.
        
        // Handle "v=0" case: Center/Left/Right logic changes.
        // Center -> New.
        // Right -> v=0.
        // Left -> Old, v!=0.
        
        // Algorithm with 0-Right invariant:
        // At u. Explore i.
        // Move u->i.
        // If Center:
        //   New v.
        //   Set v Left.
        //   Recurse...
        // If Right:
        //   v = 0.
        // If Left:
        //   Old v != 0.
        //   Identify v.
        //   Loop c in Known \ {0}:
        //     Assume v=c.
        //     Path c->0.
        //     If Right -> v=c.
        //     Return to u: 0->u.
        
        // Does Path c->0 uniquely identify c?
        // No. Multiple nodes might have same path to 0.
        // But we can check multiple paths?
        // Or verify:
        //   If we hit 0, we are at 0.
        //   Go 0->c.
        //   If v=c, we should be at v.
        //   But we are at v (conceptually).
        //   This circular check is hard.
        
        // Let's use the Mark-based ID with 0-Right.
        // u is known. v is unknown (Left).
        // We want to ID v.
        // Candidates C = Known \ {0}.
        // Iterate c in C:
        //   We are at v.
        //   Go to 0 (Assume v=c? No, just find 0).
        //   RW to Right -> 0.
        //   Go 0->u.
        //   Mark c Right. (Go u->c, Mark, go c->u).
        //   Move u->i (to v).
        //   If v Right -> v=c.
        //     Set v Left.
        //     Done.
        //   Else:
        //     Unmark c.
        
        // This is robust.
        // One catch: recursive steps.
        // When arriving at w (Center -> w), we recurse.
        // w becomes Left.
        // We are at w.
        // We need to know w's ID?
        // No, w is new, ID assigned.
        // We recurse `process_arrival`.
        // `last_resp` gives state.
        
        // Handle u=0 case in ID:
        // If u=0, we are already at 0.
        // Logic simplifies.
        
        int v_id = -1;
        vector<int> cands;
        for(int k=1; k<total_nodes; ++k) cands.push_back(k);
        
        for(int c : cands) {
             walk_to_right(); // Find 0
             vector<int> p = get_path(0, u);
             traverse_path(p); // At u
             
             // Mark c Right
             p = get_path(u, c);
             traverse_path(p); // At c
             last_resp = query(0, "right", 0); // c Right, move to adj[c][0]
             
             walk_to_right(); // Find 0
             p = get_path(0, u);
             traverse_path(p); // At u
             
             // Check v
             last_resp = query(0, "left", i); // Move u->v
             if (last_resp == "right") {
                 v_id = c;
                 last_resp = query(0, "left", 0); // Reset
                 walk_to_right();
                 break;
             } else {
                 // Unmark c
                 while(true){
                     walk_to_right(); // z
                     p = get_path(0, c); // Try 0->c
                     traverse_path(p);
                     if (last_resp == "right") {
                         last_resp = query(0, "left", 0);
                         break;
                     }
                 }
                 walk_to_right(); // 0
                 p = get_path(0, u);
                 traverse_path(p); // u
                 // Go back to v
                 last_resp = query(0, "left", i); 
                 // Now at v (Left). Loop continues.
             }
        }
        if (v_id == -1) {
            // Must be 0? Checked Right already.
            // Should be found.
        }
        adj[u][i] = v_id;
        
        // Return to u?
        // process_arrival doesn't require return.
        // But we are at 0 (after break).
        // Or at v (in loop).
        // We need to return to u for consistency?
        // No, process_arrival just updates.
        // Caller `solve_dfs` expects to continue.
        // `solve_dfs` will likely navigate to u if needed?
        // No, `solve_dfs` loop continues from u.
        // So we must end at u.
        if (last_resp == "right") {
            // At 0.
            vector<int> p = get_path(0, u);
            traverse_path(p);
        } else {
            // At v?
            // Go to 0 then u.
            walk_to_right();
            vector<int> p = get_path(0, u);
            traverse_path(p);
        }
    } else {
        // v = 0
        adj[u][i] = 0;
        // At 0.
        vector<int> p = get_path(0, u);
        traverse_path(p);
    }
}

int main() {
    srand(time(0));
    cin >> M;
    string s; cin >> s;
    for(int i=0; i<25; ++i) for(int j=0; j<25; ++j) adj[i][j] = -1;
    
    // Node 0
    total_nodes = 1;
    // Set 0 to Right
    // Current is Center.
    // 0 right 0.
    last_resp = query(0, "right", 0);
    // adj[0][0] unknown.
    // We are at adj[0][0].
    
    // We need to handle this initial move.
    // We are at w = adj[0][0].
    process_arrival(0, 0);
    
    // Now continue DFS from 0
    solve_dfs(0);
    
    return 0;
}