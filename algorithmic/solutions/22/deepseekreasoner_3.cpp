#include <bits/stdc++.h>
using namespace std;

const int MAXN = 100000 + 5;

int n;
vector<int> children[MAXN];
int parent[MAXN];
vector<int> leaf_list;
int leaf_pos[MAXN];
int first_leaf[MAXN], last_leaf[MAXN];

void dfs(int u) {
    if (children[u].empty()) {
        first_leaf[u] = last_leaf[u] = u;
        return;
    }
    first_leaf[u] = -1;
    last_leaf[u] = -1;
    for (int v : children[u]) {
        dfs(v);
        if (first_leaf[u] == -1 || leaf_pos[first_leaf[v]] < leaf_pos[first_leaf[u]]) {
            first_leaf[u] = first_leaf[v];
        }
        if (last_leaf[u] == -1 || leaf_pos[last_leaf[v]] > leaf_pos[last_leaf[u]]) {
            last_leaf[u] = last_leaf[v];
        }
    }
}

int main() {
    scanf("%d", &n);
    parent[1] = 0;
    for (int i = 2; i <= n; i++) {
        int p;
        scanf("%d", &p);
        parent[i] = p;
        children[p].push_back(i);
    }

    for (int i = 1; i <= n; i++) {
        if (children[i].empty()) {
            leaf_pos[i] = leaf_list.size();
            leaf_list.push_back(i);
        } else {
            leaf_pos[i] = -1;
        }
    }

    int k = leaf_list.size();
    dfs(1);

    printf("%d\n", n + k);

    for (int u = 1; u <= n; u++) {
        vector<int> bag;
        bag.push_back(u);
        if (u != 1) bag.push_back(parent[u]);
        if (first_leaf[u] != -1) {
            bag.push_back(first_leaf[u]);
            if (last_leaf[u] != first_leaf[u]) bag.push_back(last_leaf[u]);
        }
        sort(bag.begin(), bag.end());
        bag.erase(unique(bag.begin(), bag.end()), bag.end());
        printf("%d", (int)bag.size());
        for (int x : bag) printf(" %d", x);
        printf("\n");
    }

    for (int i = 0; i < k; i++) {
        int leaf = leaf_list[i];
        int prev_leaf = leaf_list[(i - 1 + k) % k];
        int next_leaf = leaf_list[(i + 1) % k];
        vector<int> bag;
        bag.push_back(leaf);
        bag.push_back(parent[leaf]);
        bag.push_back(prev_leaf);
        bag.push_back(next_leaf);
        sort(bag.begin(), bag.end());
        bag.erase(unique(bag.begin(), bag.end()), bag.end());
        printf("%d", (int)bag.size());
        for (int x : bag) printf(" %d", x);
        printf("\n");
    }

    for (int u = 2; u <= n; u++) {
        printf("%d %d\n", u, parent[u]);
    }
    for (int i = 0; i < k; i++) {
        int leaf = leaf_list[i];
        int id_L = n + 1 + i;
        int id_B = parent[leaf];
        printf("%d %d\n", id_L, id_B);
    }

    return 0;
}