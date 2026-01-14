#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <queue>
#include <numeric>

using namespace std;

// Global Variables
int N, M;
struct Edge {
    int u, v;
    int id;
};
vector<Edge> edges;
vector<vector<int>> adj;

// Random Number Generator
mt19937 rng(1337);

// Interaction Function
int query(const vector<int>& dirs) {
    cout << "0 ";
    for (int i = 0; i < M; ++i) {
        cout << dirs[i] << (i == M - 1 ? "" : " ");
    }
    cout << endl;
    int res;
    if (!(cin >> res)) exit(0);
    return res;
}

// Answer Function
void answer(int A, int B) {
    cout << "1 " << A << " " << B << endl;
    exit(0);
}

// BFS to compute distances
void get_dist(int start, vector<int>& dist) {
    fill(dist.begin(), dist.end(), -1);
    queue<int> q;
    q.push(start);
    dist[start] = 0;
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        for (int eid : adj[u]) {
            int v = (edges[eid].u == u ? edges[eid].v : edges[eid].u);
            if (dist[v] == -1) {
                dist[v] = dist[u] + 1;
                q.push(v);
            }
        }
    }
}

int main() {
    // Optimization for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;
    adj.resize(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        edges.push_back({u, v, i});
        adj[u].push_back(i);
        adj[v].push_back(i);
    }

    // Candidates for A and B
    vector<int> SA(N), SB(N);
    iota(SA.begin(), SA.end(), 0);
    iota(SB.begin(), SB.end(), 0);

    int query_count = 0;
    const int MAX_Q = 600;

    // We alternate strategies or pick based on effectiveness
    // Strategy 1: Distance from a pivot (handles long graphs)
    // Strategy 2: Random Permutation (handles dense/star graphs)
    
    while (query_count < MAX_Q) {
        if (SA.size() == 1 && SB.size() == 1) {
            answer(SA[0], SB[0]);
        }

        // Choose strategy
        bool use_dist = (query_count % 2 == 0); 
        // Randomize slightly
        if (rng() % 3 == 0) use_dist = !use_dist;

        vector<int> val(N);
        int max_val = N;

        if (use_dist) {
            // Pick a pivot. To improve quality, pick 'farthest' node from random
            int p = rng() % N;
            vector<int> tmp(N);
            get_dist(p, tmp);
            int best = p;
            for(int i=0; i<N; ++i) if(tmp[i] > tmp[best]) best = i;
            p = best;
            get_dist(p, val);
            max_val = 0;
            for(int v : val) max_val = max(max_val, v);
            max_val++;
        } else {
            // Random permutation
            vector<int> p(N);
            iota(p.begin(), p.end(), 0);
            shuffle(p.begin(), p.end(), rng);
            val = p;
            max_val = N;
        }

        // Try Normal Orientation: val[u] < val[v] => u->v
        // Tie break with ID to ensure strict DAG
        auto get_dir_base = [&](int i, bool reverse_graph) {
            int u = edges[i].u;
            int v = edges[i].v;
            bool u_to_v;
            if (val[u] != val[v]) u_to_v = val[u] < val[v];
            else u_to_v = u < v;
            
            if (reverse_graph) u_to_v = !u_to_v;
            
            return u_to_v ? 0 : 1; // 0: u->v, 1: v->u
        };

        bool reverse_AB = false;
        bool success = false;

        // Try Forward
        vector<int> dirs(M);
        for(int i=0; i<M; ++i) dirs[i] = get_dir_base(i, false);
        int res = query(dirs);
        query_count++;

        if (res == 1) {
            success = true;
            reverse_AB = false;
        } else {
            // Try Backward
            for(int i=0; i<M; ++i) dirs[i] = get_dir_base(i, true);
            int res2 = query(dirs);
            query_count++;
            if (res2 == 1) {
                success = true;
                reverse_AB = true;
            }
        }

        if (success) {
            // If reverse_AB is false: A -> B in base graph. Logic: U=A, V=B.
            // If reverse_AB is true: A -> B in reverse graph => B -> A in base graph. Logic: U=B, V=A.
            // We find values for U and V.

            // Binary Search for U: Find minimal k such that "U <= k" is true.
            // Predicate Q_le(k): "Is U <= k?"
            // To test, we make all nodes > k "Sinks". 
            // If U > k, U is a sink, so cannot reach V (unless U=V, impossible).
            auto check_le = [&](int k) {
                vector<int> d(M);
                for(int i=0; i<M; ++i) {
                    int u = edges[i].u, v = edges[i].v;
                    // Base direction
                    int dir = get_dir_base(i, reverse_AB);
                    
                    // Override if node > k
                    if (val[u] > k) {
                        // u is sink, force v->u
                        d[i] = 1; 
                    } else if (val[v] > k) {
                        // v is sink, force u->v
                        d[i] = 0;
                    } else {
                        d[i] = dir;
                    }
                }
                return query(d);
            };

            int L = 0, R = max_val;
            int val_U = -1;
            while (L <= R) {
                int mid = L + (R - L) / 2;
                int r = check_le(mid);
                query_count++;
                if (r == 1) {
                    val_U = mid;
                    R = mid - 1;
                } else {
                    L = mid + 1;
                }
            }

            // Binary Search for V: Find maximal k such that "V >= k" is true.
            // Predicate Q_ge(k): "Is V >= k?"
            // To test, we make all nodes < k "Sources".
            // If V < k, V is a source, cannot be reached from U.
            auto check_ge = [&](int k) {
                vector<int> d(M);
                for(int i=0; i<M; ++i) {
                    int u = edges[i].u, v = edges[i].v;
                    int dir = get_dir_base(i, reverse_AB);
                    
                    if (val[u] < k) {
                        // u is source, force u->v
                        d[i] = 0;
                    } else if (val[v] < k) {
                        // v is source, force v->u
                        d[i] = 1;
                    } else {
                        d[i] = dir;
                    }
                }
                return query(d);
            };

            L = 0, R = max_val;
            int val_V = -1;
            while (L <= R) {
                int mid = L + (R - L) / 2;
                int r = check_ge(mid);
                query_count++;
                if (r == 1) {
                    val_V = mid;
                    L = mid + 1;
                } else {
                    R = mid - 1;
                }
            }

            // Update candidates
            vector<int> next_SA, next_SB;
            if (!reverse_AB) {
                // U is A, V is B
                for(int x : SA) if (val[x] == val_U) next_SA.push_back(x);
                for(int x : SB) if (val[x] == val_V) next_SB.push_back(x);
            } else {
                // U is B, V is A
                for(int x : SA) if (val[x] == val_V) next_SA.push_back(x);
                for(int x : SB) if (val[x] == val_U) next_SB.push_back(x);
            }
            SA = next_SA;
            SB = next_SB;
        }
    }

    if (!SA.empty() && !SB.empty()) answer(SA[0], SB[0]);
    return 0;
}