#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if(!(cin >> n >> m)) return 0;
    vector<int> a(10);
    for (int i = 0; i < 10; ++i) cin >> a[i];
    
    vector<vector<int>> adj(n+1), radj(n+1);
    vector<int> deg(n+1,0);
    vector<pair<int,int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v;
        adj[u].push_back(v);
        radj[v].push_back(u);
        deg[u]++;
        edges.emplace_back(u,v);
    }
    for (int i = 1; i <= n; ++i) {
        sort(adj[i].begin(), adj[i].end());
        sort(radj[i].begin(), radj[i].end());
        adj[i].erase(unique(adj[i].begin(), adj[i].end()), adj[i].end());
        radj[i].erase(unique(radj[i].begin(), radj[i].end()), radj[i].end());
    }

    auto hasEdge = [&](int u, int v)->bool{
        auto &vec = adj[u];
        return binary_search(vec.begin(), vec.end(), v);
    };

    vector<int> bestPath;
    bestPath.reserve(n);

    auto buildFromSeed = [&](int seed)->vector<int>{
        vector<int> next(n+1, 0), prev(n+1, 0);
        vector<char> inPath(n+1, 0);
        int head = seed, tail = seed;
        inPath[seed] = 1;

        bool changed = true;
        while (changed) {
            changed = false;
            // extend tail
            bool extended = true;
            while (extended) {
                extended = false;
                for (int v : adj[tail]) {
                    if (!inPath[v]) {
                        next[tail] = v;
                        prev[v] = tail;
                        tail = v;
                        inPath[v] = 1;
                        changed = true;
                        extended = true;
                        break;
                    }
                }
            }
            // extend head (using reverse edges)
            extended = true;
            while (extended) {
                extended = false;
                for (int u : radj[head]) {
                    if (!inPath[u]) {
                        prev[head] = u;
                        next[u] = head;
                        head = u;
                        inPath[u] = 1;
                        changed = true;
                        extended = true;
                        break;
                    }
                }
            }
            // insertion pass
            bool inserted_any = false;
            for (int u = 1; u <= n; ++u) {
                if (inPath[u]) continue;
                for (int v : adj[u]) {
                    if (!inPath[v]) continue;
                    int a = prev[v];
                    if (a != 0 && hasEdge(a, u)) {
                        // insert u between a and v
                        int b = v;
                        int an = next[a]; // should be b
                        (void)an;
                        next[a] = u;
                        prev[u] = a;
                        next[u] = b;
                        prev[b] = u;
                        inPath[u] = 1;
                        inserted_any = true;
                        changed = true;
                        break;
                    }
                }
            }
            if (inserted_any) {
                // after insertions, try to extend ends again in next loop
            }
        }
        // build path vector
        vector<int> path;
        path.reserve(n);
        int cur = head;
        while (cur != 0) {
            path.push_back(cur);
            cur = next[cur];
        }
        return path;
    };

    // choose seeds: max out-degree, some random vertices, and 1
    vector<int> seeds;
    seeds.push_back(1);
    int maxd = 1;
    for (int i = 2; i <= n; ++i) if (deg[i] > deg[maxd]) maxd = i;
    seeds.push_back(maxd);

    // random seeds
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist(1, n);
    int extra = 6; // number of random tries
    for (int i = 0; i < extra; ++i) seeds.push_back(dist(rng));

    // deduplicate seeds
    sort(seeds.begin(), seeds.end());
    seeds.erase(unique(seeds.begin(), seeds.end()), seeds.end());

    for (int s : seeds) {
        vector<int> cand = buildFromSeed(s);
        if (cand.size() > bestPath.size()) bestPath.swap(cand);
        if ((int)bestPath.size() == n) break;
    }

    // Fallback if somehow empty
    if (bestPath.empty()) bestPath.push_back(1);

    cout << bestPath.size() << "\n";
    for (size_t i = 0; i < bestPath.size(); ++i) {
        if (i) cout << ' ';
        cout << bestPath[i];
    }
    cout << "\n";
    return 0;
}