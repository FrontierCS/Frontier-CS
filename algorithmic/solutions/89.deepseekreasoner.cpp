#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> parent;
vector<vector<int>> children;
vector<int> subtree_size;
vector<bool> is_chain;
vector<vector<int>> subtree_list;
int total_queries = 0;
long long total_set_size = 0;

void flush() {
    cout.flush();
}

bool query_on_path(int a, int b, int c) {
    cout << "? 2 " << a << " " << b << " " << c << endl;
    flush();
    int ans;
    cin >> ans;
    if (ans == -1) exit(0);
    total_queries++;
    total_set_size += 2; // because set size = 2 (b and c)
    return ans == 1;
}

void add_to_ancestors(int v, int p) {
    int cur = p;
    while (cur != 0) {
        subtree_size[cur]++;
        subtree_list[cur].push_back(v);
        cur = parent[cur];
    }
}

void update_chain(int p) {
    int cur = p;
    while (cur != 0) {
        bool chain_status;
        if (children[cur].empty()) {
            chain_status = true;
        } else if (children[cur].size() == 1) {
            int only_child = children[cur][0];
            chain_status = is_chain[only_child];
        } else {
            chain_status = false;
        }
        is_chain[cur] = chain_status;
        cur = parent[cur];
    }
}

void attach(int v, int p) {
    parent[v] = p;
    children[p].push_back(v);
    add_to_ancestors(v, p);
    update_chain(p);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n;

    parent.resize(n+1, 0);
    children.resize(n+1);
    subtree_size.resize(n+1, 1);
    is_chain.resize(n+1, true);
    subtree_list.resize(n+1);
    for (int i = 1; i <= n; i++) {
        subtree_list[i].push_back(i);
    }

    for (int v = 2; v <= n; v++) {
        int u = 1;
        while (true) {
            if (children[u].empty()) {
                attach(v, u);
                break;
            }
            if (is_chain[u]) {
                // get chain from u to leaf
                vector<int> chain;
                int cur = u;
                while (true) {
                    chain.push_back(cur);
                    if (children[cur].empty()) break;
                    // is_chain[cur] true => exactly one child
                    cur = children[cur][0];
                }
                // binary search for deepest node in chain such that v is in its subtree
                int lo = 0, hi = (int)chain.size() - 1;
                int ans = 0;
                while (lo <= hi) {
                    int mid = (lo + hi) / 2;
                    if (mid == 0) {
                        // u itself always satisfies
                        ans = mid;
                        lo = mid +