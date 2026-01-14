#include <bits/stdc++.h>
using namespace std;

int n, m, start_vertex, base_move_count;
vector<vector<int>> adj;
vector<int> deg;
vector<bool> visited;
map<vector<int>, vector<int>> signature_to_vertices;

vector<int> get_sorted_neighbor_degrees(int v) {
    vector<int> res;
    for (int u : adj[v]) res.push_back(deg[u]);
    sort(res.begin(), res.end());
    return res;
}

void precompute_signatures() {
    signature_to_vertices.clear();
    for (int v = 1; v <= n; ++v) {
        vector<int> sig = get_sorted_neighbor_degrees(v);
        signature_to_vertices[sig].push_back(v);
    }
}

// Identify current vertex from description: degree d, vector of pairs (degree, flag)
int identify(int d, vector<pair<int, int>>& desc, int prev) {
    // Build signature (sorted neighbor degrees) from description
    vector<int> sig;
    for (auto& p : desc) sig.push_back(p.first);
    sort(sig.begin(), sig.end());

    // Get candidate vertices with this signature
    if (signature_to_vertices.find(sig) == signature_to_vertices.end())
        return -1;
    vector<int> candidates = signature_to_vertices[sig];

    // Sort description pairs for comparison
    vector<pair<int, int>> desc_sorted = desc;
    sort(desc_sorted.begin(), desc_sorted.end());

    vector<int> good_candidates;
    for (int v : candidates) {
        // Build expected pairs for vertex v
        vector<pair<int, int>> expected;
        for (int u : adj[v]) {
            expected.emplace_back(deg[u], visited[u] ? 1 : 0);
        }
        sort(expected.begin(), expected.end());
        if (expected == desc_sorted) {
            good_candidates.push_back(v);
        }
    }

    if (good_candidates.size() == 1)
        return good_candidates[0];
    else if (good_candidates.size() > 1) {
        // Use previous vertex to disambiguate
        if (prev != -1) {
            vector<int> filtered;
            for (int v : good_candidates) {
                if (find(adj[prev].begin(), adj[prev].end(), v) != adj[prev].end()) {
                    filtered.push_back(v);
                }
            }
            if (filtered.size() == 1)
                return filtered[0];
        }
        // Still ambiguous: choose the smallest id
        return good_candidates[0];
    } else {
        return -1;
    }
}

// Find the next vertex to move to: the first step on a shortest path to the closest unvisited vertex.
int find_next_vertex(int cur) {
    vector<int> dist(n + 1, -1);
    vector<int> parent(n + 1, -1);
    queue<int> q;
    dist[cur] = 0;
    q.push(cur);
    while (!q.empty()) {
        int v = q.front(); q.pop();
        for (int u : adj[v]) {
            if (dist[u] == -1) {
                dist[u] = dist[v] + 1;
                parent[u] = v;
                q.push(u);
            }
        }
    }
    // Find unvisited vertex with minimal distance
    int target = -1, min_dist = n + 1;
    for (int v = 1; v <= n; ++v) {
        if (!visited[v] && dist[v] != -1 && dist[v] < min_dist) {
            min_dist = dist[v];
            target = v;
        }
    }
    if (target == -1) return -1; // all visited
    // Reconstruct the first step
    int v = target;
    while (parent[v] != cur) v = parent[v];
    return v;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    cin >> t;
    while (t--) {
        cin >> n >> m >> start_vertex >> base_move_count;
        adj.assign(n + 1, {});
        deg.assign(n + 1, 0);
        for (int i = 0; i < m; ++i) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        for (int v = 1; v <= n; ++v) deg[v] = adj[v].size();

        precompute_signatures();
        visited.assign(n + 1, false);

        int cur = start_vertex;
        visited[cur] = true;
        int prev = -1;

        // Read the first vertex description (skip possible empty lines)
        string line;
        getline(cin, line); // consume the newline after the last integer
        while (line.empty()) getline(cin, line);

        while (true) {
            // Parse current description
            stringstream ss(line);
            int d;
            ss >> d;
            vector<pair<int, int>> desc(d);
            for (int i = 0; i < d; ++i) {
                int degree, flag;
                ss >> degree >> flag;
                desc[i] = {degree, flag};
            }

            // Identify current vertex
            int identified = identify(d, desc, prev);
            if (identified == -1) identified = cur; // fallback
            cur = identified;
            visited[cur] = true;

            // Decide which neighbor to move to
            int next_v = find_next_vertex(cur);
            if (next_v == -1) {
                // All vertices visited – any move will trigger AC
                next_v = adj[cur][0];
            }

            // Choose the port that matches next_v's degree and visited status
            int port = 1;
            for (int i = 0; i < d; ++i) {
                if (desc[i].first == deg[next_v] && desc[i].second == (visited[next_v] ? 1 : 0)) {
                    port = i + 1; // 1-indexed
                    break;
                }
            }

            // Output the move
            cout << port << endl;
            cout.flush();

            // Read response (either description, AC, or F)
            string response;
            if (!getline(cin, response)) break;
            if (response.substr(0, 2) == "AC") {
                break; // map completed successfully
            } else if (response.substr(0, 1) == "F") {
                break; // move limit exceeded, proceed to next map
            } else {
                line = response;
                prev = cur;
            }
        }
    }
    return 0;
}