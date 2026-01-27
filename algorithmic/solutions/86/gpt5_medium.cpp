#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 1005;

int n;
vector<vector<int>> adj;
vector<char> present;
set<pair<int,int>> edges_set;

long long queries_count = 0;
unordered_map<long long, int> cache;

// Utility to add/remove edges in current tree structure
void addEdge(int u, int v) {
    if (u == v) return;
    if (u > v) swap(u, v);
    if (!edges_set.count({u,v})) {
        edges_set.insert({u,v});
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
}
void removeEdge(int u, int v) {
    if (u == v) return;
    if (u > v) swap(u, v);
    if (edges_set.count({u,v})) {
        edges_set.erase({u,v});
        auto &au = adj[u];
        auto &av = adj[v];
        au.erase(remove(au.begin(), au.end(), v), au.end());
        av.erase(remove(av.begin(), av.end(), u), av.end());
    }
}

// Query function with caching; triple treated as unordered (sorted)
int query_median(int a, int b, int c) {
    vector<int> t = {a,b,c};
    sort(t.begin(), t.end());
    long long key = ((long long)t[0] << 42) ^ ((long long)t[1] << 21) ^ (long long)t[2];
    auto it = cache.find(key);
    if (it != cache.end()) return it->second;
    cout << "0 " << a << " " << b << " " << c << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) {
        exit(0);
    }
    cache[key] = res;
    queries_count++;
    return res;
}

// Get any node in the component
int anyNodeInC(const vector<char>& inC) {
    for (int i = 1; i <= n; ++i) if (inC[i]) return i;
    return -1;
}

// BFS restricted to nodes in inC, from start, optionally forbidding certain immediate neighbor edges from the starting node
vector<int> bfs_restrict(int start, const vector<char>& inC, int forbidFromStart1 = -1, int forbidFromStart2 = -1) {
    vector<int> vis(n+1, 0);
    vector<int> comp;
    queue<int> q;
    vis[start] = 1;
    q.push(start);
    comp.push_back(start);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int v : adj[u]) {
            if (!inC[v]) continue;
            if (u == start && (v == forbidFromStart1 || v == forbidFromStart2)) continue;
            if (!vis[v]) {
                vis[v] = 1;
                q.push(v);
                comp.push_back(v);
            }
        }
    }
    return comp;
}

// Find farthest node from s within inC; returns pair(node, parent array)
pair<int, vector<int>> bfs_farthest(int s, const vector<char>& inC) {
    vector<int> dist(n+1, -1), parent(n+1, -1);
    queue<int> q;
    dist[s] = 0;
    q.push(s);
    int far = s;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        if (dist[u] > dist[far]) far = u;
        for (int v : adj[u]) {
            if (!inC[v]) continue;
            if (dist[v] == -1) {
                dist[v] = dist[u] + 1;
                parent[v] = u;
                q.push(v);
            }
        }
    }
    return {far, parent};
}

// Compute diameter path within the component inC
vector<int> getDiameterPath(const vector<char>& inC) {
    int r = anyNodeInC(inC);
    if (r == -1) return {};
    auto p1 = bfs_farthest(r, inC);
    int a = p1.first;
    auto p2 = bfs_farthest(a, inC);
    int b = p2.first;
    vector<int> path;
    for (int x = b; x != -1; x = p2.second[x]) path.push_back(x);
    reverse(path.begin(), path.end());
    return path;
}

// Update inC mask to exactly the list of nodes 'lst'
void setMaskToList(vector<char>& inC, const vector<int>& lst) {
    vector<char> newMask(n+1, 0);
    for (int x : lst) newMask[x] = 1;
    inC.swap(newMask);
}

// Insert a vertex v into the current tree using diameter-guided search and median queries
void insertVertex(int v) {
    // If no nodes present (shouldn't happen with n>=3), add and return
    int presentCount = 0;
    for (int i = 1; i <= n; ++i) if (present[i]) presentCount++;
    if (presentCount == 0) {
        present[v] = 1;
        return;
    }
    if (presentCount == 1) {
        int u = anyNodeInC(present);
        addEdge(u, v);
        present[v] = 1;
        return;
    }
    vector<char> inC(n+1, 0);
    for (int i = 1; i <= n; ++i) if (present[i]) inC[i] = 1;

    while (true) {
        int cnt = 0, last = -1;
        for (int i = 1; i <= n; ++i) if (inC[i]) { cnt++; last = i; }
        if (cnt == 1) {
            addEdge(last, v);
            present[v] = 1;
            return;
        }
        vector<int> diamPath = getDiameterPath(inC);
        int k = (int)diamPath.size();
        if (k == 1) {
            addEdge(diamPath[0], v);
            present[v] = 1;
            return;
        }
        int a = diamPath.front();
        int b = diamPath.back();
        int t = query_median(a, b, v);
        if (t == a) {
            // Keep side near a: forbid going towards diamPath[1]
            vector<int> comp = bfs_restrict(a, inC, diamPath[1], -1);
            setMaskToList(inC, comp);
        } else if (t == b) {
            vector<int> comp = bfs_restrict(b, inC, diamPath[k-2], -1);
            setMaskToList(inC, comp);
        } else {
            // t is somewhere on the (true) path between a and b
            int neighbor1 = -1, neighbor2 = -1;
            if (!present[t]) {
                // locate edge to split via binary search on path indices
                int low = 1, high = k-1, pos = k-1;
                while (low <= high) {
                    int mid = (low + high) >> 1;
                    int s = query_median(diamPath[mid], b, v);
                    if (s == t) {
                        pos = mid;
                        high = mid - 1;
                    } else {
                        // s should be diamPath[mid]
                        low = mid + 1;
                    }
                }
                int j = pos - 1;
                int x = diamPath[j];
                int y = diamPath[j+1];
                // split edge (x,y) by inserting t
                removeEdge(x, y);
                addEdge(x, t);
                addEdge(t, y);
                present[t] = 1;
                neighbor1 = x;
                neighbor2 = y;
            } else {
                // t already present; find its neighbors on diamPath
                int idx = -1;
                for (int i = 0; i < k; ++i) if (diamPath[i] == t) { idx = i; break; }
                if (idx != -1) {
                    if (idx > 0) neighbor1 = diamPath[idx-1];
                    if (idx+1 < k) neighbor2 = diamPath[idx+1];
                }
            }
            if (t == v) {
                // v lies on the path; already inserted by splitting
                // No further connection needed
                return;
            }
            // shrink to the "middle" component around t, excluding both directions along the diameter path
            vector<int> comp = bfs_restrict(t, inC, neighbor1, neighbor2);
            setMaskToList(inC, comp);
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;
    adj.assign(n+1, {});
    present.assign(n+1, 0);

    // Initialize with nodes 1 and 2
    present[1] = 1;
    if (n >= 2) {
        present[2] = 1;
        addEdge(1, 2);
    }

    for (int v = 3; v <= n; ++v) {
        if (!present[v]) {
            insertVertex(v);
        }
    }
    // Some nodes might have been inserted out of order via queries
    for (int v = 1; v <= n; ++v) {
        if (!present[v]) {
            insertVertex(v);
        }
    }

    // Output final edges
    cout << "1";
    for (auto &e : edges_set) {
        cout << " " << e.first << " " << e.second;
    }
    cout << endl;
    cout.flush();
    return 0;
}