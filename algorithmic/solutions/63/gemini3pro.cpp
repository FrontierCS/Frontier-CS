#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <random>

using namespace std;

int N, M;
struct Edge {
    int u, v;
    int id;
};
vector<Edge> edges;
vector<vector<pair<int, int>>> adj;

// Query function
// output 0 d0 d1 ... dm-1
// returns 1 or 0
int query(const vector<int>& dirs) {
    cout << "0";
    for (int d : dirs) {
        cout << " " << d;
    }
    cout << endl;
    int res;
    cin >> res;
    return res;
}

void answer(int A, int B) {
    cout << "1 " << A << " " << B << endl;
    exit(0);
}

// BFS to get distances
vector<int> get_dists(int start_node) {
    vector<int> d(N, -1);
    queue<int> q;
    q.push(start_node);
    d[start_node] = 0;
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        for (auto& edge : adj[u]) {
            int v = edge.first;
            if (d[v] == -1) {
                d[v] = d[u] + 1;
                q.push(v);
            }
        }
    }
    return d;
}

struct Constraint {
    int root;
    int depth_val;
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;
    adj.resize(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        edges.push_back({u, v, i});
        adj[u].push_back({v, i});
        adj[v].push_back({u, i});
    }

    vector<Constraint> consA, consB;
    int queries_left = 600;
    
    // Random generator
    mt19937 rng(1337);
    vector<int> p(N);
    for(int i=0; i<N; ++i) p[i] = i;
    shuffle(p.begin(), p.end(), rng);
    
    int root_idx = 0;
    
    // We try random roots until we solve or run out of safe query count
    while (queries_left > 35 && root_idx < N) {
        int r = p[root_idx++];
        vector<int> d = get_dists(r);
        
        // Prepare dirs for d[u] < d[v] (BFS DAG)
        vector<int> dirs(M);
        auto set_dir = [&](int k, int u, int v) {
            // Wants u -> v
            if (edges[k].u == u && edges[k].v == v) dirs[k] = 0;
            else dirs[k] = 1;
        };

        for (const auto& e : edges) {
            if (d[e.u] < d[e.v]) set_dir(e.id, e.u, e.v);
            else if (d[e.v] < d[e.u]) set_dir(e.id, e.v, e.u);
            else set_dir(e.id, e.u, e.v); // Arbitrary for same depth
        }
        
        if (queries_left <= 0) break;
        queries_left--;
        int res = query(dirs);
        
        bool modeA = false; // A -> B (d[A] < d[B])
        bool modeB = false; // B -> A (d[B] < d[A])
        
        if (res == 1) {
            modeA = true;
        } else {
            // Try reverse orientation
            for (const auto& e : edges) {
                if (d[e.v] < d[e.u]) set_dir(e.id, e.u, e.v);
                else if (d[e.u] < d[e.v]) set_dir(e.id, e.v, e.u);
                else set_dir(e.id, e.u, e.v);
            }
            if (queries_left <= 0) break;
            queries_left--;
            int res2 = query(dirs);
            if (res2 == 1) modeB = true;
        }
        
        if (!modeA && !modeB) continue; // No information from this root
        
        // Found order.
        // If modeA: d[A] < d[B]. Source=A, Sink=B.
        // If modeB: d[B] < d[A]. Source=B, Sink=A.
        
        // 1. Find d[Sink]. Binary Search.
        // Constraint: path allowed in depth <= M.
        // i.e. Block nodes with depth > M.
        
        int L = 0, R = N; 
        int depthSink = N;
        
        while (L <= R) {
            int mid = L + (R - L) / 2;
            
            // Build query blocking > mid
            // Base orientation: Small d -> Large d
            for (const auto& e : edges) {
                int u = e.u, v = e.v;
                if (d[u] > d[v]) swap(u, v); 
                // Natural dir u -> v (d[u] <= d[v])
                
                if (d[v] > mid) {
                    // Block entry to v. Orient v -> u.
                    set_dir(e.id, v, u);
                } else {
                    // Allow u -> v
                    set_dir(e.id, u, v);
                }
            }
            
            if (queries_left <= 0) break;
            queries_left--;
            int q_res = query(dirs);
            
            if (q_res == 1) {
                depthSink = mid;
                R = mid - 1;
            } else {
                L = mid + 1;
            }
        }
        
        // 2. Find d[Source]. BS.
        // Constraint: path allowed in depth >= M.
        // i.e. Block nodes with depth < M.
        
        L = 0; R = depthSink;
        int depthSource = 0;
        
        while (L <= R) {
            int mid = L + (R - L) / 2;
            
            // Block < mid
            for (const auto& e : edges) {
                int u = e.u, v = e.v;
                if (d[u] > d[v]) swap(u, v);
                
                if (d[u] < mid) {
                    // Block exit from u. Orient v -> u.
                    set_dir(e.id, v, u);
                } else {
                    set_dir(e.id, u, v);
                }
            }
            
            if (queries_left <= 0) break;
            queries_left--;
            int q_res = query(dirs);
            
            if (q_res == 1) {
                depthSource = mid;
                L = mid + 1;
            } else {
                R = mid - 1;
            }
        }
        
        if (modeA) {
            consA.push_back({r, depthSource});
            consB.push_back({r, depthSink});
        } else {
            consB.push_back({r, depthSource});
            consA.push_back({r, depthSink});
        }
        
        // Optimization: if we have enough constraints, check if unique
        if (consA.size() >= 10) break;
    }
    
    // Solve using gathered constraints
    vector<bool> possA(N, true), possB(N, true);
    
    for (size_t i = 0; i < consA.size(); ++i) {
        int r = consA[i].root;
        int dA = consA[i].depth_val;
        int dB = consB[i].depth_val;
        
        vector<int> d = get_dists(r);
        
        for (int u = 0; u < N; ++u) {
            if (possA[u] && d[u] != dA) possA[u] = false;
            if (possB[u] && d[u] != dB) possB[u] = false;
        }
    }
    
    int ansA = -1, ansB = -1;
    // Find distinct pair
    for (int u = 0; u < N; ++u) if (possA[u]) {
        for (int v = 0; v < N; ++v) if (possB[v]) {
            if (u != v) {
                ansA = u; 
                ansB = v;
                // Prefer breaking if just one match, but here we take first valid.
                // With 10+ constraints, uniqueness is highly likely.
                goto done;
            }
        }
    }
    
    done:
    answer(ansA, ansB);

    return 0;
}