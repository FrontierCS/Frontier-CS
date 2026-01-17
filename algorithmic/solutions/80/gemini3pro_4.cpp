#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <algorithm>
#include <map>
#include <random>
#include <set>

using namespace std;

int M;
int N_found = 0;
struct Node {
    int id;
    vector<int> adj;
    bool is_root;
};
vector<Node> nodes;
mt19937 rng(1337);

void action(int stone_move, string side, int take_passage) {
    cout << stone_move << " " << side << " " << take_passage << endl;
}

string read_input() {
    string s;
    cin >> s;
    if (s == "treasure") exit(0);
    return s;
}

// Global state for DFS
// We need to keep track of the graph
// nodes[1] is root.

// Navigation helper
// BFS to find path from u to v
vector<int> find_path(int u, int v) {
    if (u == v) return {};
    queue<pair<int, vector<int>>> q;
    q.push({u, {}});
    vector<int> visited(nodes.size() + 1, 0);
    visited[u] = 1;
    
    while (!q.empty()) {
        auto [curr, path] = q.front();
        q.pop();
        
        if (curr == v) return path;
        
        if (curr > (int)nodes.size()) continue; // Should not happen
        
        for (int i = 0; i < M; ++i) {
            int next_node = nodes[curr-1].adj[i];
            if (next_node != -1 && !visited[next_node]) {
                visited[next_node] = 1;
                vector<int> new_path = path;
                new_path.push_back(i);
                q.push({next_node, new_path});
                
                if (next_node == v) return new_path;
            }
        }
    }
    return {}; // Should not happen in SC graph
}

void walk_path(const vector<int>& path) {
    for (int p : path) {
        string resp = read_input();
        // We assume we are at a known node, so we just pass through
        // Keep stone at 0 Left (or Right for Root).
        // To maintain state, we must output 0 Side 0 if we take 0?
        // Wait, if we take p, we do `0 Side p`.
        // We need to know current node to decide side.
        // But actually, we don't change side. We just output side same as current.
        // Since we read "Left" or "Right", we just output "0 Left p" or "0 Right p".
        // Actually, we can just force "Left" if not Root.
        // But if we are at Root, we MUST keep "Right".
        // The input tells us where the stone is.
        // If "center", it's unexpected (only new nodes).
        
        string side = "Left";
        if (resp == "Right") side = "Right";
        else if (resp == "center") {
             // Should not happen during navigation on visited graph
             side = "Left"; 
        }
        
        // We keep stone at relative 0.
        action(0, side, p);
    }
}

void reset_to_root() {
    while (true) {
        string s = read_input();
        if (s == "Right") return; // Found Root
        // Else, random walk
        int p = rng() % M;
        // Keep "Left" marker
        action(0, "Left", p);
    }
}

void go_to(int target) {
    // First, find where we are? 
    // This function assumes we are at a KNOWN node if called in certain context,
    // OR we are lost.
    // However, to be safe, we Reset to Root then walk.
    // Optimization: if we track current node, we can path directly.
    // But for safety and simplicity (and since context might be "after identify"),
    // let's always reset to root.
    // Unless target is Root, then just reset.
    
    // Check if we are already at Root?
    // We can't peek input without consuming.
    // But the loop in reset_to_root consumes input.
    
    reset_to_root();
    // Now at Root (Node 1)
    if (target == 1) return;
    
    vector<int> path = find_path(1, target);
    walk_path(path);
}

// Forward decl
void explore(int u);

// Returns ID of the node we are AT.
// prev_u, prev_edge are used to return to location if needed during identification
int handle_arrival(int prev_u, int prev_edge) {
    string s = read_input();
    
    if (s == "center") {
        // New node
        N_found++;
        int new_id = N_found;
        nodes.push_back({new_id, vector<int>(M, -1), false});
        
        // Mark it Left and take edge 0
        action(0, "Left", 0);
        // We moved to child 0 of new_id
        return new_id; 
    }
    
    if (s == "Right") {
        // Root
        return 1;
    }
    
    // Visited node (Left)
    // Identify which one
    vector<int> candidates;
    for (int i = 2; i <= N_found; ++i) candidates.push_back(i);
    
    // Filter candidates
    while (candidates.size() > 1) {
        // Pick a path that splits candidates
        // We try random paths of short length
        vector<int> best_path;
        int best_split_diff = 10000;
        
        // Try 10 random paths
        for (int t = 0; t < 20; ++t) {
            vector<int> path;
            int len = 1 + (rng() % 8); // length 1..8
            for(int k=0; k<len; ++k) path.push_back(rng() % M);
            
            int hits_root = 0;
            for (int cand : candidates) {
                // Simulate
                int curr = cand;
                bool ok = true;
                for (int p : path) {
                    if (nodes[curr-1].adj[p] == -1) { 
                        // Path leaves known graph? Should be rare if mostly visited
                        // Treat as 'unknown' outcome? Or just avoid such path.
                        // Actually, if we hit -1, we can't simulate.
                        ok = false; break;
                    }
                    curr = nodes[curr-1].adj[p];
                }
                if (ok && curr == 1) hits_root++;
            }
            
            int diff = abs((int)candidates.size() - 2 * hits_root);
            if (diff < best_split_diff) {
                best_split_diff = diff;
                best_path = path;
            }
            if (diff <= 1) break; 
        }
        
        if (best_path.empty()) {
            // Fallback: just pick path to root of first candidate
            best_path = find_path(candidates[0], 1);
            if (best_path.empty()) {
                 // Should not happen
                 best_path.push_back(0);
            }
        }
        
        // Execute best_path
        walk_path(best_path);
        // Check where we are
        string res = read_input();
        bool is_root = (res == "Right");
        
        // Filter
        vector<int> next_cands;
        for (int cand : candidates) {
            int curr = cand;
            bool ok = true;
            for (int p : best_path) {
                if (nodes[curr-1].adj[p] == -1) { ok = false; break; }
                curr = nodes[curr-1].adj[p];
            }
            // If path goes out of known, we assume it didn't match observation if observation was Root
            // If observation was Left, and simulation unknown, we keep it? 
            // Risky. But with N=20, graph is dense quickly.
            // If unknown, we can't rule out.
            
            bool sim_root = (ok && curr == 1);
            if (is_root == sim_root) {
                next_cands.push_back(cand);
            }
        }
        candidates = next_cands;
        
        // We are at result of path.
        // Need to go back to `prev_u` -> `prev_edge` -> `arrival_node`
        // But simpler: just go back to `prev_u`, and re-take `prev_edge`.
        // Note: ResetToRoot works from anywhere.
        
        // However, we effectively performed a move sequence.
        // We need to return to the node we are identifying to try again if needed?
        // Actually, we need to return to the node we were identifying.
        // But `go_to` requires a target ID. We don't know it!
        // We know predecessors.
        // So we go to `prev_u`, take `prev_edge`.
        // Then we are back at the unknown node.
        
        // Optimization: if result was Root, we are at Root.
        if (is_root) {
            // At Root.
            if (prev_u != 1) {
                vector<int> p = find_path(1, prev_u);
                walk_path(p);
            }
        } else {
            // Not at Root.
            reset_to_root();
            vector<int> p = find_path(1, prev_u);
            walk_path(p);
        }
        // Take the edge to return to unknown node
        action(0, (prev_u == 1 ? "Right" : "Left"), prev_edge);
        
        // Read input will be done at start of next loop or function exit?
        // No, we are inside `handle_arrival`, we already consumed the initial input.
        // But now we moved back. We need to consume the input from the move `prev_u -> prev_edge`.
        // But `handle_arrival` expects to handle the input.
        // Wait, the loop continues. We need to read input to check if we are back?
        // No, we know we are back.
        // We must NOT consume input here, or we must handle it.
        // The `walk_path` consumes inputs.
        // The last `action` produces an input.
        // We need to verify we are still seeing what we expect?
        // Actually, for the next iteration of logic, we don't need input, we just need physical presence.
        // But `walk_path` calls `read_input`.
        // The `action` above triggers a response. We should read it?
        // Yes, to check if "treasure". But also it's the state for next path execution.
        if (candidates.size() > 1) {
             string dummy = read_input(); // Consume the input from returning to node
             // Should be same as original 's' ("Left")
        }
    }
    
    return candidates[0];
}

void explore(int u) {
    // We assume we are at `u`.
    // However, if `u` was just discovered, we are actually at `u->adj[0]`.
    // We need to detect this state.
    // We can check if `nodes[u-1].adj[0]` is set?
    // No, we set it inside explore.
    
    // Correct logic:
    // If `u` is new, we have implicitly taken edge 0.
    // So we handle k=0 specially.
    
    // Check if adj[0] is -1. If so, we are at child 0 physically.
    bool just_arrived_via_0 = (nodes[u-1].adj[0] == -1);
    
    for (int k = 0; k < M; ++k) {
        if (just_arrived_via_0 && k == 0) {
            // We are at child of 0.
            int v = handle_arrival(u, 0);
            nodes[u-1].adj[0] = v;
            
            // If v is new (id > u normally, or just check if adj is empty)
            // If v was returned by handle_arrival as NEW, it means we are at v's child 0.
            // We can detect if v is new by checking its visited status or ID logic.
            // Since IDs are incremental, if v > current max known before call?
            // Easier: check if `nodes[v-1].adj` is all -1.
            // But we need to distinguish "newly created" from "visited but unexplored".
            // Actually `handle_arrival` creates the node. So its adj is all -1.
            // We can check if v was just created.
            // Let's pass a flag or check if v's edges are empty.
            // Since graph is SC, if v is old, it might have edges?
            // No, we fill edges as we explore.
            // We can track `visited` array separately.
            
            bool v_is_new = false;
            // A node is new if we haven't explored it.
            // But we might have visited it and left?
            // The `handle_arrival` logic: "If center -> New node".
            // So we know from return value?
            // Let's rely on checking if we have explored `v`.
            // We can use a `visited_flag` in Node.
            // But `handle_arrival` creates a node, so it's not visited/explored yet.
            
            // Just check if we need to recurse.
            // We recurse if it's the first time we see `v`.
            // We can use a global `explored` set.
            static vector<bool> explored(25, false);
            
            if (!explored[v]) {
                explored[v] = true;
                explore(v);
            }
            
            // Return to u
            go_to(u);
            
        } else {
            if (nodes[u-1].adj[k] != -1) continue; // Already mapped
            
            // Take edge k
            string side = (u == 1 ? "Right" : "Left");
            action(0, side, k);
            
            int v = handle_arrival(u, k);
            nodes[u-1].adj[k] = v;
            
            static vector<bool> explored(25, false);
            // Re-init explored if needed? No, static is fine as long as size is enough.
            if (explored.size() < nodes.size() + 1) explored.resize(nodes.size() + 1, false);
            
            // Check if v is newly discovered (created in handle_arrival)
            // If v was just created, it has no edges mapped.
            // If v is old, we might have fully explored it or not.
            // But we only recurse if it's the *first* time we discover it (tree edge).
            // If handle_arrival returned "Left" -> it's a back/cross edge -> don't recurse.
            // If handle_arrival returned "center" -> tree edge -> recurse.
            // We can detect this by checking if v's ID was just added?
            // Or simpler: handle_arrival returns ID.
            // If v was "center", handle_arrival returns new ID.
            // If v was "Left/Right", returns old ID.
            // We can pass a bool ref to handle_arrival.
            
            // BUT, `handle_arrival` returns ID. We can compare with `N_found` before call?
            // No, `handle_arrival` increments N_found.
            // Let's modify `handle_arrival` to return pair.
            // Can't easily change signature now, let's use check.
            // If v corresponds to a node that has empty adj vector and we know it was just made?
            // Actually, we can just check `explored[v]`.
            // If it was just created, explored[v] is false.
            // If it was old, explored[v] is likely true (since we explore immediately on discovery).
            // Wait, what if we reached an old node that hasn't been explored?
            // DFS property: if we reach a visited node, it's either currently being visited (ancestor) or fully visited.
            // So we never recurse on an old node.
            // So `!explored[v]` is sufficient?
            // Yes. When `handle_arrival` makes a new node, it doesn't set explored.
            // When we return old ID, it was set explored when first discovered.
            
            if (!explored[v]) {
                explored[v] = true;
                explore(v);
            }
            
            go_to(u);
        }
    }
}

int main() {
    cin >> M;
    string s = read_input();
    
    // Initial state: At Root.
    // Must mark Root.
    nodes.push_back({1, vector<int>(M, -1), true});
    N_found = 1;
    
    // Mark Root "Right" and move to child 0
    action(0, "Right", 0);
    
    // We are now at child 0 of Root.
    // This matches the "just arrived via 0" state for Root if we consider
    // Root was "new" and we took edge 0.
    // So we can call explore(1).
    // Note: explore(1) logic for k=0 will handle the current position.
    
    static vector<bool> explored(25, false);
    explored[1] = true;
    explore(1);
    
    return 0;
}