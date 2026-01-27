#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<int> s(n), t(n);
    for (int i = 0; i < n; ++i) cin >> s[i];
    for (int i = 0; i < n; ++i) cin >> t[i];
    vector<vector<int>> g(n);
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v;
        --u; --v;
        g[u].push_back(v);
        g[v].push_back(u);
    }
    
    // Compute connected components
    vector<int> comp_id(n, -1);
    vector<vector<int>> comps;
    int cid = 0;
    for (int i = 0; i < n; ++i) {
        if (comp_id[i] == -1) {
            queue<int> q;
            q.push(i);
            comp_id[i] = cid;
            comps.push_back({});
            comps.back().push_back(i);
            while (!q.empty()) {
                int u = q.front(); q.pop();
                for (int v : g[u]) {
                    if (comp_id[v] == -1) {
                        comp_id[v] = cid;
                        comps.back().push_back(v);
                        q.push(v);
                    }
                }
            }
            cid++;
        }
    }
    int C = cid;
    
    // Determine for each component whether target has both colors
    vector<bool> comp_target_both(C, false);
    for (int cc = 0; cc < C; ++cc) {
        bool has0 = false, has1 = false;
        for (int u : comps[cc]) {
            if (t[u] == 0) has0 = true;
            if (t[u] == 1) has1 = true;
        }
        comp_target_both[cc] = (has0 && has1);
    }
    
    vector<int> cur = s;
    vector<vector<int>> states;
    states.push_back(cur);
    
    auto is_equal = [&](const vector<int>& a, const vector<int>& b)->bool{
        for (int i = 0; i < n; ++i) if (a[i] != b[i]) return false;
        return true;
    };
    
    const int MAX_STEPS = 20000;
    
    auto compute_fixable = [&](const vector<int>& cur_state) {
        vector<int> fixable;
        for (int i = 0; i < n; ++i) {
            if (cur_state[i] == t[i]) continue;
            int need = t[i];
            bool ok = false;
            for (int nb : g[i]) {
                if (cur_state[nb] == need) { ok = true; break; }
            }
            if (ok) fixable.push_back(i);
        }
        return fixable;
    };
    
    auto unique_color_in_comp = [&](int comp, int color, const vector<int>& cur_state)->pair<int,int>{
        int cnt = 0, last = -1;
        for (int u : comps[comp]) {
            if (cur_state[u] == color) { cnt++; last = u; }
        }
        return {cnt, last};
    };
    
    auto bfs_path_to_color = [&](int target_node, int color, const vector<int>& cur_state)->vector<int>{
        int comp = comp_id[target_node];
        vector<int> parent(n, -1);
        vector<int> dist(n, INT_MAX);
        queue<int> q;
        // Multi-source BFS
        for (int u : comps[comp]) {
            if (cur_state[u] == color) {
                dist[u] = 0;
                parent[u] = -1;
                q.push(u);
            }
        }
        if (dist[target_node] == 0) {
            // Already has desired color (should not happen if mismatch), but handle
            vector<int> path;
            path.push_back(target_node);
            return path;
        }
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : g[u]) {
                if (comp_id[v] != comp) continue;
                if (dist[v] == INT_MAX) {
                    dist[v] = dist[u] + 1;
                    parent[v] = u;
                    q.push(v);
                }
            }
        }
        vector<int> path;
        if (dist[target_node] == INT_MAX) return path; // empty, no path found
        int v = target_node;
        while (v != -1) {
            path.push_back(v);
            v = parent[v];
        }
        reverse(path.begin(), path.end()); // from source to target
        return path;
    };
    
    while (!is_equal(cur, t) && (int)states.size() - 1 < MAX_STEPS) {
        // Step 1: fix all nodes that can copy desired color from a neighbor
        vector<int> fixable = compute_fixable(cur);
        if (!fixable.empty()) {
            vector<int> next = cur;
            for (int i : fixable) {
                next[i] = t[i];
            }
            states.push_back(next);
            cur.swap(next);
            continue;
        }
        // Step 2: move desired color one step closer for some node
        int chosen = -1;
        for (int i = 0; i < n; ++i) {
            if (cur[i] != t[i]) { chosen = i; break; }
        }
        if (chosen == -1) break; // should not happen
        
        int need = t[chosen];
        int comp = comp_id[chosen];
        
        // if there is no node with color 'need' in this component, it's impossible (but guaranteed solvable)
        auto path = bfs_path_to_color(chosen, need, cur);
        if (path.empty()) {
            // No path (shouldn't happen if problem guarantees solution and we keep colors)
            // As a fallback, break to avoid infinite loop
            break;
        }
        if ((int)path.size() == 1) {
            // Already correct color at chosen (contradiction with mismatch), but handle: skip
            continue;
        }
        if ((int)path.size() == 2) {
            // Neighbor has desired color; but then chosen should be fixable. Handle by direct fix.
            vector<int> next = cur;
            next[chosen] = need;
            states.push_back(next);
            cur.swap(next);
            continue;
        }
        int v = path[(int)path.size() - 2];        // neighbor of chosen along path
        int u = path[(int)path.size() - 3];        // predecessor of v along path, has color 'need'
        
        // Ensure not to eliminate a required color in this component
        if (comp_target_both[comp]) {
            int opp = 1 - need;
            auto [cntOpp, uniqueOpp] = unique_color_in_comp(comp, opp, cur);
            if (cntOpp == 1 && cur[v] == opp) {
                // Create an extra 'opp' by copying from uniqueOpp to one of its neighbors
                int src = uniqueOpp;
                int y = -1;
                for (int nb : g[src]) {
                    if (comp_id[nb] == comp && cur[nb] != opp) { y = nb; break; }
                }
                if (y != -1) {
                    vector<int> next = cur;
                    next[y] = opp; // y copies from src (uniqueOpp)
                    states.push_back(next);
                    cur.swap(next);
                }
            }
        }
        // Move color 'need' from u to v
        {
            vector<int> next = cur;
            // v copies from u
            next[v] = cur[u];
            states.push_back(next);
            cur.swap(next);
        }
        // Loop continues; now chosen should be fixable in next iteration
    }
    
    // If still not equal due to step cap (unlikely), try to finish with remaining steps one-by-one greedily
    while (!is_equal(cur, t) && (int)states.size() - 1 < MAX_STEPS) {
        vector<int> fixable = compute_fixable(cur);
        if (fixable.empty()) break;
        vector<int> next = cur;
        for (int i : fixable) next[i] = t[i];
        states.push_back(next);
        cur.swap(next);
    }
    
    // If not finished, as a last resort try single-node moves along paths until done (still respecting cap)
    while (!is_equal(cur, t) && (int)states.size() - 1 < MAX_STEPS) {
        int chosen = -1;
        for (int i = 0; i < n; ++i) if (cur[i] != t[i]) { chosen = i; break; }
        if (chosen == -1) break;
        int need = t[chosen];
        auto path = bfs_path_to_color(chosen, need, cur);
        if (path.size() < 2) break;
        if (path.size() == 2) {
            vector<int> next = cur; next[chosen] = need;
            states.push_back(next); cur.swap(next);
            continue;
        }
        int v = path[(int)path.size() - 2];
        int u = path[(int)path.size() - 3];
        int comp = comp_id[chosen];
        if (comp_target_both[comp]) {
            int opp = 1 - need;
            auto [cntOpp, uniqueOpp] = unique_color_in_comp(comp, opp, cur);
            if (cntOpp == 1 && cur[v] == opp) {
                int src = uniqueOpp;
                int y = -1;
                for (int nb : g[src]) {
                    if (comp_id[nb] == comp && cur[nb] != opp) { y = nb; break; }
                }
                if (y != -1 && (int)states.size() - 1 < MAX_STEPS) {
                    vector<int> next = cur; next[y] = opp;
                    states.push_back(next); cur.swap(next);
                }
            }
        }
        if ((int)states.size() - 1 >= MAX_STEPS) break;
        vector<int> next = cur; next[v] = cur[u];
        states.push_back(next); cur.swap(next);
    }
    
    // Ensure final state equals target; if not, attempt final greedy wave within remaining steps
    while (!is_equal(cur, t) && (int)states.size() - 1 < MAX_STEPS) {
        vector<int> fixable = compute_fixable(cur);
        if (fixable.empty()) break;
        vector<int> next = cur;
        for (int i : fixable) next[i] = t[i];
        states.push_back(next); cur.swap(next);
    }
    
    // If still not equal, we might be stuck (shouldn't happen). If so, force print what we have (invalid),
    // but per problem guarantees and algorithm, this should not happen for valid inputs.
    
    int k = max(0, (int)states.size() - 1);
    cout << k << "\n";
    for (auto &st : states) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << st[i];
        }
        cout << "\n";
    }
    return 0;
}