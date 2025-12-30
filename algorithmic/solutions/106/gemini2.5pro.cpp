#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

map<vector<int>, int> query_cache;

int do_query(vector<int> s) {
    if (s.empty()) {
        return 0;
    }
    sort(s.begin(), s.end());
    if (query_cache.count(s)) {
        return query_cache[s];
    }

    cout << "? " << s.size() << endl;
    for (size_t i = 0; i < s.size(); ++i) {
        cout << s[i] << (i == s.size() - 1 ? "" : " ");
    }
    cout << endl;

    int m;
    cin >> m;
    if (m == -1) exit(0);
    return query_cache[s] = m;
}

int count_edges_between(int u, const vector<int>& S) {
    if (S.empty()) return 0;
    vector<int> s_with_u = S;
    s_with_u.push_back(u);
    return do_query(s_with_u) - do_query(S);
}

int find_one_neighbor(int u, const vector<int>& S) {
    if (S.empty()) return -1;
    
    int l = 0, r = S.size() - 1;
    while(l < r) {
        int mid = l + (r - l) / 2;
        vector<int> prefix;
        for(int i = l; i <= mid; ++i) prefix.push_back(S[i]);
        
        if (count_edges_between(u, prefix) > 0) {
            r = mid;
        } else {
            l = mid + 1;
        }
    }
    return S[l];
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    vector<int> color(n + 1, -1);
    vector<int> parent(n + 1, 0);
    vector<int> P[2];
    vector<int> q;

    color[1] = 0;
    P[0].push_back(1);
    q.push_back(1);
    int head = 0;

    vector<bool> is_colored(n + 1, false);
    is_colored[1] = true;

    while(head < q.size()){
        int u = q[head++];

        vector<int> uncolored_nodes;
        for(int i = 1; i <= n; ++i){
            if(!is_colored[i]){
                uncolored_nodes.push_back(i);
            }
        }
        if(uncolored_nodes.empty()) continue;
        
        int num_neighbors_in_uncolored = count_edges_between(u, uncolored_nodes);

        while(num_neighbors_in_uncolored > 0){
            int v = find_one_neighbor(u, uncolored_nodes);
            
            is_colored[v] = true;
            color[v] = 1 - color[u];
            parent[v] = u;

            if(count_edges_between(v, P[color[v]]) > 0){
                int w = find_one_neighbor(v, P[color[v]]);
                
                vector<int> path_v, path_w;
                int curr = v;
                while(curr != 0){
                    path_v.push_back(curr);
                    curr = parent[curr];
                }
                curr = w;
                while(curr != 0){
                    path_w.push_back(curr);
                    curr = parent[curr];
                }
                reverse(path_v.begin(), path_v.end());
                reverse(path_w.begin(), path_w.end());

                size_t lca_depth = 0;
                while(lca_depth < path_v.size() && lca_depth < path_w.size() && path_v[lca_depth] == path_w[lca_depth]){
                    lca_depth++;
                }
                lca_depth--;

                vector<int> cycle;
                for(size_t i = path_v.size() - 1; i > lca_depth; --i) cycle.push_back(path_v[i]);
                cycle.push_back(path_v[lca_depth]);
                for(size_t i = lca_depth + 1; i < path_w.size(); ++i) cycle.push_back(path_w[i]);
                
                cout << "N " << cycle.size() << endl;
                for(size_t i=0; i<cycle.size(); ++i) {
                    cout << cycle[i] << (i == cycle.size()-1 ? "" : " ");
                }
                cout << endl;
                return 0;
            }

            P[color[v]].push_back(v);
            q.push_back(v);
            
            auto it = find(uncolored_nodes.begin(), uncolored_nodes.end(), v);
            uncolored_nodes.erase(it);

            num_neighbors_in_uncolored--;
        }
    }

    cout << "Y " << P[0].size() << endl;
    for (size_t i = 0; i < P[0].size(); ++i) {
        cout << P[0][i] << (i == P[0].size() - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}