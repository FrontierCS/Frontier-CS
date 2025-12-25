#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <tuple>

using namespace std;

map<pair<int, int>, long long> memo;

long long query(int u, int v) {
    if (u == v) return 0;
    if (u > v) swap(u, v);
    if (memo.count({u, v})) {
        return memo[{u, v}];
    }
    cout << "? " << u << " " << v << endl;
    long long d;
    cin >> d;
    return memo[{u, v}] = d;
}

void solve() {
    int n;
    cin >> n;
    memo.clear();

    if (n == 1) {
        cout << "!" << endl;
        return;
    }

    vector<tuple<int, int, long long>> edges;
    vector<vector<pair<int, long long>>> adj(n + 1);

    auto add_edge = [&](int u, int v, long long w) {
        edges.emplace_back(u, v, w);
        adj[u].push_back({v, w});
        adj[v].push_back({u, w});
    };
    
    if (n == 2) {
        long long d = query(1, 2);
        cout << "! 1 2 " << d << endl;
        return;
    }

    int A = 1, B = 2;
    long long D = query(1, 2);
    add_edge(1, 2, D);

    vector<int> p_path(n + 1);
    vector<long long> dists(n + 1);

    for (int i = 3; i <= n; ++i) {
        long long dist_Ai = query(A, i);
        long long dist_Bi = query(B, i);

        long long dist_A_p = (D + dist_Ai - dist_Bi) / 2;
        
        fill(p_path.begin(), p_path.end(), 0);
        fill(dists.begin(), dists.end(), -1);
        vector<int> q;
        q.reserve(i);
        q.push_back(A);
        
        dists[A] = 0;
        p_path[A] = 0;
        
        int head = 0;
        while(head < q.size()){
            int u = q[head++];
            for(auto& edge : adj[u]){
                int v = edge.first;
                long long w = edge.second;
                if(v != p_path[u]){
                    p_path[v] = u;
                    dists[v] = dists[u] + w;
                    q.push_back(v);
                }
            }
        }

        int curr = B;
        while(dists[curr] > dist_A_p) {
            curr = p_path[curr];
        }
        int p = curr;

        add_edge(p, i, dist_Ai - dist_A_p);
        
        if (dist_Ai > D) {
            B = i;
            D = dist_Ai;
        } else if (dist_Bi > D) {
            A = i;
            D = dist_Bi;
        }
    }

    cout << "! ";
    for (size_t i = 0; i < edges.size(); ++i) {
        cout << get<0>(edges[i]) << " " << get<1>(edges[i]) << " " << get<2>(edges[i]) << (i == edges.size() - 1 ? "" : " ");
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.flush();
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}