#include <iostream>
#include <vector>
#include <numeric>
#include <map>
#include <algorithm>
#include <functional>

using namespace std;

void solve() {
    int n;
    cin >> n;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<long long> f(n + 1);
    for (int i = 1; i <= n; ++i) {
        cout << "? 1 1 " << i << endl;
        cin >> f[i];
    }

    vector<int> candidates;
    for (int i = 1; i <= n; ++i) {
        if (f[i] == 1 || f[i] == -1) {
            candidates.push_back(i);
        }
    }

    map<vector<int>, vector<int>> value_map;
    vector<int> parent(n + 1);
    vector<int> q;
    q.reserve(n);

    for (int c : candidates) {
        fill(parent.begin(), parent.end(), 0);
        q.clear();
        q.push_back(c);
        parent[c] = c;
        int head = 0;
        while(head < q.size()){
            int u = q[head++];
            for(int v : adj[u]){
                if(parent[v] == 0){
                    parent[v] = u;
                    q.push_back(v);
                }
            }
        }

        vector<int> values(n + 1);
        values[c] = f[c];
        for (int i = 1; i <= n; ++i) {
            if (i == c) continue;
            values[i] = f[i] - f[parent[i]];
        }
        
        vector<int> v_res(n);
        for(int i = 0; i < n; ++i) v_res[i] = values[i + 1];
        value_map[v_res].push_back(c);
    }

    if (value_map.size() == 1) {
        const auto& values_vec = value_map.begin()->first;
        cout << "! ";
        for (int i = 0; i < n; ++i) {
            cout << values_vec[i] << (i == n - 1 ? "" : " ");
        }
        cout << endl;
        return;
    }

    auto it1 = value_map.begin();
    auto it2 = next(it1);
    
    int c1 = it1->second[0];
    const auto& v1 = it1->first;

    int c2 = it2->second[0];
    const auto& v2 = it2->first;

    vector<int> size1(n + 1);
    function<void(int, int)> dfs_size1 = 
        [&](int u, int p) {
        size1[u] = 1;
        for (int v : adj[u]) {
            if (v == p) continue;
            dfs_size1(v, u);
            size1[u] += size1[v];
        }
    };
    dfs_size1(c1, 0);

    long long E1 = 0;
    for (int i = 1; i <= n; ++i) {
        E1 += (long long)(v1[i-1]) * size1[i];
    }

    vector<int> size2(n + 1);
    function<void(int, int)> dfs_size2 = 
        [&](int u, int p) {
        size2[u] = 1;
        for (int v : adj[u]) {
            if (v == p) continue;
            dfs_size2(v, u);
            size2[u] += size2[v];
        }
    };
    dfs_size2(c2, 0);

    long long E2 = 0;
    for (int i = 1; i <= n; ++i) {
        E2 += (long long)(v2[i-1]) * size2[i];
    }
    
    const vector<int>* final_values_ptr = nullptr;

    if (E1 != E2) {
        cout << "? 1 " << n;
        for (int i = 1; i <= n; ++i) cout << " " << i;
        cout << endl;
        long long S;
        cin >> S;
        if (S == E1) {
            final_values_ptr = &v1;
        } else {
            final_values_ptr = &v2;
        }
    } else {
        vector<int> color(n + 1, -1);
        vector<int> part_A;
        q.clear();
        q.push_back(1);
        color[1] = 0;
        int head = 0;
        while(head < q.size()) {
            int u = q[head++];
            if (color[u] == 0) part_A.push_back(u);
            for(int v : adj[u]) {
                if(color[v] == -1) {
                    color[v] = 1 - color[u];
                    q.push_back(v);
                }
            }
        }
        
        vector<int> count_in_A1(n+1, 0);
        function<void(int, int)> dfs_count1 = 
            [&](int u, int p) {
            if (color[u] == 0) count_in_A1[u] = 1; else count_in_A1[u] = 0;
            for (int v : adj[u]) {
                if (v == p) continue;
                dfs_count1(v, u);
                count_in_A1[u] += count_in_A1[v];
            }
        };
        dfs_count1(c1, 0);
        long long E1_A = 0;
        for(int i=1; i<=n; ++i) E1_A += (long long)v1[i-1] * count_in_A1[i];

        vector<int> count_in_A2(n+1, 0);
        function<void(int, int)> dfs_count2 = 
            [&](int u, int p) {
            if (color[u] == 0) count_in_A2[u] = 1; else count_in_A2[u] = 0;
            for (int v : adj[u]) {
                if (v == p) continue;
                dfs_count2(v, u);
                count_in_A2[u] += count_in_A2[v];
            }
        };
        dfs_count2(c2, 0);
        long long E2_A = 0;
        for(int i=1; i<=n; ++i) E2_A += (long long)v2[i-1] * count_in_A2[i];
        
        cout << "? 1 " << part_A.size();
        for(int node : part_A) cout << " " << node;
        cout << endl;
        long long S_A;
        cin >> S_A;
        if (S_A == E1_A) {
            final_values_ptr = &v1;
        } else {
            final_values_ptr = &v2;
        }
    }


    cout << "! ";
    for (int i = 0; i < n; ++i) {
        cout << (*final_values_ptr)[i] << (i == n - 1 ? "" : " ");
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}