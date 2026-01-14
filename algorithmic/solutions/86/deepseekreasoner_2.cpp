#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> children[1005];
int parent[1005];
int depth[1005];
int subtree_size[1005];
int heavy_child[1005];

int ask(int a, int b, int c) {
    cout << "0 " << a << " " << b << " " << c << endl;
    int res;
    cin >> res;
    return res;
}

bool is_ancestor(int x, int v) {
    // root is 1
    int m = ask(1, x, v);
    return (m == x);
}

void update_heavy(int p) {
    // update subtree sizes and heavy child from p upward
    int u = p;
    while (u != 0) {
        subtree_size[u]++;
        int w = parent[u];
        if (w != 0) {
            if (heavy_child[w] == -1 || subtree_size[u] > subtree_size[heavy_child[w]]) {
                heavy_child[w] = u;
            }
        }
        u = w;
    }
}

int find_parent(int v) {
    int u = 1; // start from root
    while (true) {
        if (children[u].empty()) {
            return u;
        }
        // get heavy path from u
        vector<int> path;
        int cur = u;
        while (cur != -1) {
            path.push_back(cur);
            cur = heavy_child[cur];
        }
        // binary search for deepest ancestor on heavy path
        int lo = 0, hi = (int)path.size() - 1;
        int best = -1;
        while (lo <= hi) {
            int mid = (lo + hi) / 2;
            int x = path[mid];
            if (is_ancestor(x, v)) {
                best = mid;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }
        // best must be found because at least root is ancestor
        int x = path[best];
        u = x;
        // collect light children of u
        vector<int> light;
        for (int c : children[u]) {
            if (c != heavy_child[u]) {
                light.push_back(c);
            }
        }
        if (light.empty()) {
            return u;
        }
        // tournament among light children
        vector<int> cand = light;
        while (cand.size() > 1) {
            int a = cand.back(); cand.pop_back();
            int b = cand.back(); cand.pop_back();
            int m = ask(a, b, v);
            if (m == a) {
                cand.push_back(a);
            } else if (m == b) {
                cand.push_back(b);
            } else {
                // m == u (or possibly something else, but should be u)
                // both eliminated
            }
        }
        if (cand.empty()) {
            return u;
        } else {
            // exactly one candidate
            u = cand[0];
            // continue loop
        }
    }
}

int main() {
    cin >> n;
    // initialize root
    parent[1] = 0;
    depth[1] = 0;
    subtree_size[1] = 1;
    heavy_child[1] = -1;
    children[1].clear();

    vector<int> order;
    for (int i = 2; i <= n; i++) order.push_back(i);
    random_shuffle(order.begin(), order.end());

    for (int v : order) {
        int p = find_parent(v);
        parent[v] = p;
        depth[v] = depth[p] + 1;
        children[p].push_back(v);
        subtree_size[v] = 1;
        heavy_child[v] = -1;
        update_heavy(p);
    }

    // output edges
    cout << "1";
    for (int i = 2; i <= n; i++) {
        cout << " " << parent[i] << " " << i;
    }
    cout << endl;
    return 0;
}