#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    if (n == 1) {
        cout << "Y 1" << endl;
        cout << "1" << endl;
        return 0;
    }
    vector<vector<int>> tree(n + 1);
    vector<int> parent(n + 1, 0);
    vector<int> color(n + 1, -1);
    color[1] = 0;
    parent[1] = -1;
    vector<int> visited = {1};
    vector<int> unvisited;
    for (int i = 2; i <= n; ++i) {
        unvisited.push_back(i);
    }
    int e_current = 0; // singleton

    auto query = [&](vector<int> s) -> int {
        if (s.empty()) return 0;
        sort(s.begin(), s.end());
        cout << "? " << s.size() << endl;
        for (size_t i = 0; i < s.size(); ++i) {
            cout << s[i];
            if (i + 1 < s.size()) cout << " ";
        }
        cout << endl;
        cout.flush();
        int m;
        cin >> m;
        if (m == -1) exit(0);
        return m;
    };

    while (!unvisited.empty()) {
        // Find u in unvisited connected to visited
        vector<int> candidates = unvisited;
        while (candidates.size() > 1) {
            size_t mid = candidates.size() / 2;
            vector<int> left(candidates.begin(), candidates.begin() + mid);
            vector<int> right(candidates.begin() + mid, candidates.end());
            // cross to left
            int e_t = query(left);
            vector<int> temp_visited = visited;
            temp_visited.insert(temp_visited.end(), left.begin(), left.end());
            int e_ct = query(temp_visited);
            int cross = e_ct - e_current - e_t;
            if (cross > 0) {
                candidates = left;
            } else {
                candidates = right;
            }
        }
        int u = candidates[0];

        // Remove u from unvisited
        auto it = find(unvisited.begin(), unvisited.end(), u);
        if (it != unvisited.end()) {
            unvisited.erase(it);
        }

        // Find v in visited connected to u
        vector<int> cands_v = visited;
        while (cands_v.size() > 1) {
            size_t mid = cands_v.size() / 2;
            vector<int> left(cands_v.begin(), cands_v.begin() + mid);
            vector<int> right(cands_v.begin() + mid, cands_v.end());
            // deg to left
            int e_s = query(left);
            vector<int> temp;
            temp.push_back(u);
            temp.insert(temp.end(), left.begin(), left.end());
            sort(temp.begin(), temp.end());
            int e_us = query(temp);
            int d = e_us - e_s;
            if (d > 0) {
                cands_v = left;
            } else {
                cands_v = right;
            }
        }
        int v = cands_v[0];

        // Now add edge v-u
        tree[v].push_back(u);
        tree[u].push_back(v);
        parent[u] = v;
        color[u] = 1 - color[v];

        // Update e_current
        vector<int> old_visited = visited;
        vector<int> temp_new = old_visited;
        temp_new.push_back(u);
        sort(temp_new.begin(), temp_new.end());
        int e_new = query(temp_new);
        int deg = e_new - e_current;
        if (deg <= 0) exit(0);
        e_current = e_new;
        visited.push_back(u);
    }

    // Now build A and B
    vector<int> A, B;
    for (int i = 1; i <= n; ++i) {
        if (color[i] == 0) A.push_back(i);
        else B.push_back(i);
    }

    int e_A = A.empty() ? 0 : query(A);
    int e_B = B.empty() ? 0 : query(B);

    if (e_A == 0 && e_B == 0) {
        // Bipartite, output A
        cout << "Y " << A.size() << endl;
        for (size_t i = 0; i < A.size(); ++i) {
            cout << A[i];
            if (i + 1 < A.size()) cout << " ";
        }
        cout << endl;
        return 0;
    }

    // Not bipartite, find odd cycle
    vector<int> part = (e_A > 0 && (e_B == 0 || A.size() <= B.size())) ? A : B;
    bool is_A = (part == A);
    int e_part = is_A ? e_A : e_B;

    // Find v in part with deg >0 in part -v
    int vv = -1;
    vector<int> S;
    for (int cand_v : part) {
        S.clear();
        for (int x : part) {
            if (x != cand_v) S.push_back(x);
        }
        int e_s = S.empty() ? 0 : query(S);
        int deg_v = e_part - e_s;
        if (deg_v > 0) {
            vv = cand_v;
            break;
        }
    }
    if (vv == -1) exit(0); // should not happen

    // Now binary search in S for w connected to vv
    vector<int> candidates = S;
    while (candidates.size() > 1) {
        size_t mid = candidates.size() / 2;
        vector<int> left(candidates.begin(), candidates.begin() + mid);
        vector<int> right(candidates.begin() + mid, candidates.end());
        // deg to left
        int e_s_left = query(left);
        vector<int> temp;
        temp.push_back(vv);
        temp.insert(temp.end(), left.begin(), left.end());
        sort(temp.begin(), temp.end());
        int e_vleft = query(temp);
        int dleft = e_vleft - e_s_left;
        if (dleft > 0) {
            candidates = left;
        } else {
            candidates = right;
        }
    }
    int w = candidates[0];

    // Now find path from vv to w in tree
    vector<int> par(n + 1, -1);
    vector<bool> vis(n + 1, false);
    queue<int> q;
    q.push(vv);
    vis[vv] = true;
    par[vv] = -1;
    bool found = false;
    while (!q.empty() && !found) {
        int cur = q.front(); q.pop();
        for (int nei : tree[cur]) {
            if (!vis[nei]) {
                vis[nei] = true;
                par[nei] = cur;
                q.push(nei);
                if (nei == w) {
                    found = true;
                    break;
                }
            }
        }
    }
    if (!found) exit(0); // should not

    // Reconstruct path
    vector<int> path;
    int cur = w;
    while (cur != -1) {
        path.push_back(cur);
        cur = par[cur];
    }
    reverse(path.begin(), path.end()); // path[0] = vv, path.back() = w

    // Output
    cout << "N " << path.size() << endl;
    for (size_t i = 0; i < path.size(); ++i) {
        cout << path[i];
        if (i + 1 < path.size()) cout << " ";
    }
    cout << endl;

    return 0;
}